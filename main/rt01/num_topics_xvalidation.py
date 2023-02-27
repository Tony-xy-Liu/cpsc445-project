import os
from concurrent.futures import ProcessPoolExecutor as Exe
from datetime import datetime as dt
import numpy as np
import tomotopy as tp
from tomotopy.utils import Corpus

CORPUS_FOLDER = "./cache/corpus"
MODEL_FOLDER = "./cache/models"
SUMMARY_FOLDER = f"./cache/summaries"
if not os.path.exists(MODEL_FOLDER): os.makedirs(MODEL_FOLDER)
if not os.path.exists(SUMMARY_FOLDER): os.makedirs(SUMMARY_FOLDER)

def test_num_topics(train_file: str):
    def _log(x):
        timestamp = f"{dt.now().strftime('%H:%M:%S')}"
        print(f"{timestamp}:{train_file}> {x}")

    save_path = f"{CORPUS_FOLDER}/{train_file}"
    test_corpus_path = save_path.replace('train', 'test')
    toks = save_path.split('/')[-1].split('_')
    k = int(toks[0][1:])
    cross_val_i = toks[1]
    iters = [100]

    todo = False
    for i in iters:
        name = f"k{k}_{cross_val_i}_iter{i}"
        model_save = f"{MODEL_FOLDER}/{name}.bin"
        if not os.path.exists(model_save):
            todo = True
            break
    if not todo: return
        
    _log("loading data")
    train_x = Corpus.load(save_path)
    test_x = Corpus.load(test_corpus_path)
    model = tp.CTModel(k=k, rm_top=5, min_cf=10)
    model.add_corpus(train_x)
    
    current_iter = 0
    def _run_test(total_iter: int):
        nonlocal current_iter
        iter = total_iter - current_iter
        assert iter > 0
        name = f"k{k}_{cross_val_i}_iter{total_iter}"
        model_save = f"{MODEL_FOLDER}/{name}.bin"
        current_iter += total_iter
        if os.path.exists(model_save):
            nonlocal model
            model = model.load(model_save)
            return
        
        try:
            model.train(iter=iter, workers=16)
            log_ll = np.mean(model.infer(test_x)[1])
            model.save(model_save)
            with open(f"{SUMMARY_FOLDER}/{name}.summary.txt", 'w') as f:
                model.summary(topic_word_top_n=10, file=f)
                f.writelines([l+'\n' for l in [
                    "",
                    "",
                    f"log likelihood:",
                    f"{log_ll}",
                ]])
        except:
            _log(f"failed: {name}")

    for i in iters:
        _log(f"training to {i}")
        _run_test(i)

    _log("completed")
    return train_file

corpus_saves = []
for f in os.listdir(CORPUS_FOLDER):
    if f.endswith('test'): continue
    corpus_saves.append(f)
corpus_saves = sorted(corpus_saves, key=lambda s: int(s.split('_')[0][1:]))

with Exe(max_workers=1) as exe:
    for r in exe.map(test_num_topics, corpus_saves, chunksize=1):
        pass
