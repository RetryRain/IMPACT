import numpy as np

from clustering.embedder import embed_texts, set_model
from tests.fixtures import FakeModel


def test_embed_texts_returns_normalized_batch():
    set_model(FakeModel())
    vectors = embed_texts(["alpha", "beta"])
    assert vectors.shape == (2, 384)
    norms = np.linalg.norm(vectors, axis=1)
    np.testing.assert_allclose(norms, 1.0, rtol=1e-5)


def test_embed_texts_empty_input():
    vectors = embed_texts([])
    assert vectors.shape == (0, 384)
