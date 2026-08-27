# Dostoevsky Model

A small project exploring whether a language model fine-tuned exclusively on Fyodor Dostoevsky's works can generate prose in his style, given a prompt.

## Idea

Rather than prompting a general-purpose frontier model to "write like Dostoevsky," this project trains a model directly on his corpus, with the goal of producing text that captures his voice, rhythm, and themes more faithfully than a model that has only seen a handful of examples in-context.

**Longer-term idea:** extend this into a "write an essay like this author" tool — fine-tune small models on a single author's body of work so each one writes essays in that author's distinct style, potentially outperforming general frontier models on style-fidelity (if not raw quality) precisely because each model is a specialist.

## Contents

- `build_corpus.py` — script to assemble the training corpus from source texts
- `dostoevsky_corpus.txt` — the resulting corpus
- `tokenizerDosto.ipynb` — tokenizer setup / experimentation notebook

## Status

Early / experimental. Not yet a trained model — currently focused on corpus construction and tokenization.


