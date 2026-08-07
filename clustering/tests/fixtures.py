import numpy as np


class FakeModel:
    def encode(self, sentences, *, batch_size, normalize_embeddings, show_progress_bar):
        del batch_size, show_progress_bar
        rows = []
        for sentence in sentences:
            seed = sum(ord(char) for char in sentence) % 97
            vector = np.full(384, seed / 100.0, dtype=np.float32)
            if normalize_embeddings:
                vector = vector / np.linalg.norm(vector)
            rows.append(vector)
        return np.vstack(rows)
