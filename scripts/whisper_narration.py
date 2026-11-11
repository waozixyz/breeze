"""Read-only Whisper QA, including the complete audio of long practice cues.

Uses Transformers' documented sequential long-form decoder, without truncation
or supplied reference text. Models must already exist locally.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

from ming_narration import file_hash

LANGUAGES = ('en', 'es', 'cs', 'de', 'fr', 'pt', 'ru', 'ja', 'ko', 'zh')

MODEL = 'openai/whisper-small'
REVISION = '973afd24965f72e36ca33b3055d56a652f456b4d'


class Transcriber:
    def __init__(self, model_path, threads=2):
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                          OMP_NUM_THREADS=str(threads), MKL_NUM_THREADS=str(threads))
        import torch
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
        torch.set_num_threads(threads)
        self.torch = torch
        self.processor = WhisperProcessor.from_pretrained(model_path, local_files_only=True)
        self.model = WhisperForConditionalGeneration.from_pretrained(
            model_path, local_files_only=True).eval()

    def transcribe(self, path, language):
        if language not in LANGUAGES:
            raise ValueError('Unsupported narration QA language')
        import numpy as np
        raw = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1',
                              '-i', str(path), '-f', 'f32le', '-ar', '16000', '-ac', '1', '-'],
                             check=True, capture_output=True).stdout
        audio = np.frombuffer(raw, dtype='<f4').copy()
        if not 0 < len(audio) <= 16000 * 120 or not np.isfinite(audio).all():
            raise ValueError('Invalid or oversized narration for QA')
        features = self.processor(audio, sampling_rate=16000, return_tensors='pt',
                                  truncation=False, padding='longest', return_attention_mask=True)
        with self.torch.inference_mode():
            tokens = self.model.generate(
                input_features=features.input_features, attention_mask=features.attention_mask,
                language=language, task='transcribe', return_timestamps=True,
                max_new_tokens=440, do_sample=False)
        text = self.processor.batch_decode(tokens, skip_special_tokens=True)[0].strip()
        return dict(text=text, language=language, model=MODEL, revision=REVISION,
                    audio_sha256=file_hash(path), seconds=len(audio) / 16000,
                    input_samples=len(audio), truncation=False, long_form=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--audio', type=Path)
    parser.add_argument('--language', choices=LANGUAGES)
    parser.add_argument('--batch', type=Path)
    args = parser.parse_args()
    if not args.batch and not (args.audio and args.language):
        parser.error('use --audio and --language, or --batch')
    rows = json.loads(args.batch.read_text()) if args.batch else [dict(audio=args.audio, language=args.language)]
    model = Transcriber(args.model)
    results = [model.transcribe(row['audio'], row['language']) for row in rows]
    print(json.dumps(results if args.batch else results[0], ensure_ascii=False))


if __name__ == '__main__':
    main()
