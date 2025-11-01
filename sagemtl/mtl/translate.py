# Blood-Dawn — translator backends
from dataclasses import dataclass

import torch


@dataclass
class _Base:
    device: str

    def translate(self, text: str) -> str:
        raise NotImplementedError


class _HF(_Base):
    def __init__(self, model: str, device: str):
        from transformers import pipeline

        device_map = (
            0
            if (device == "cuda" or (device == "auto" and torch.cuda.is_available()))
            else -1
        )
        self.pipe = pipeline("translation", model=model, device=device_map)
        self.device = "cuda" if device_map == 0 else "cpu"

    def translate(self, text: str) -> str:
        out = self.pipe(text, max_length=2048)
        return out[0]["translation_text"]


class _CT2(_Base):
    def __init__(self, model: str, device: str):
        import ctranslate2
        import sentencepiece as spm
        from pathlib import Path
        from typing import Any

        # model is a directory path exported for CTranslate2
        self.translator = ctranslate2.Translator(
            model,
            device=(
                "cuda"
                if (
                    device == "cuda" or (device == "auto" and torch.cuda.is_available())
                )
                else "cpu"
            ),
        )
        # assume sentencepiece model files named src.model and tgt.model beside model dir
        # Instantiate processors and load models explicitly. Type as Any to satisfy static
        # checkers that may not have full stubs for sentencepiece.
        self.src_sp: Any = spm.SentencePieceProcessor()
        self.src_sp.Load(str((Path(model) / "src.model").resolve()))
        self.tgt_sp: Any = spm.SentencePieceProcessor()
        self.tgt_sp.Load(str((Path(model) / "tgt.model").resolve()))
        self.device = "cuda" if self.translator.device == "cuda" else "cpu"

    def translate(self, text: str) -> str:
        toks = self.src_sp.encode(text, out_type=str)
        pred = self.translator.translate_batch([toks])
        ids = self.tgt_sp.decode(pred[0].hypotheses[0])
        return ids


def get_translator(backend: str, model: str, device: str):
    if backend == "ct2":
        return _CT2(model, device)
    return _HF(model, device)
