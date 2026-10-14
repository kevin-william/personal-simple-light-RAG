from pathlib import Path
from typing import Literal
from hashlib import sha256
import json

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore', case_sensitive=False)
    root: Path = ROOT
    model_repo_id: str = 'unsloth/Phi-4-mini-instruct-GGUF'
    model_filename: str = 'Phi-4-mini-instruct.Q8_0.gguf'
    model_revision: str = ''
    embedding_model_name: str = 'BAAI/bge-m3'
    embedding_model_revision: str = ''
    models_dir: Path = Path('models')
    chroma_persist_dir: Path = Path('data/chroma')
    collection_name: str = 'documents'
    llm_backend: Literal['cuda', 'cpu'] = 'cuda'
    embedding_device: Literal['cuda', 'cpu'] = 'cuda'
    n_gpu_layers: int = Field(-1, ge=-1)
    context_size: int = Field(4096, ge=512)
    max_response_tokens: int = Field(512, gt=0)
    chunk_size_chars: int = Field(800, gt=0)
    chunk_overlap_chars: int = Field(150, ge=0)
    top_k: int = Field(4, gt=0)
    memory_summary_max_tokens: int = Field(192, gt=0)
    query_resolution_max_tokens: int = Field(256, gt=0)
    embedding_batch_size: int = Field(8, gt=0)
    embedding_max_tokens: int = Field(512, ge=16, le=8192)
    memory_mode: Literal['resident', 'alternating'] = 'resident'

    @model_validator(mode='after')
    def validate_settings(self):
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError('CHUNK_OVERLAP_CHARS deve ser menor que CHUNK_SIZE_CHARS.')
        if self.max_response_tokens + 64 >= self.context_size:
            raise ValueError('Reserve espaço de entrada além de MAX_RESPONSE_TOKENS.')
        if max(self.memory_summary_max_tokens, self.query_resolution_max_tokens) + 128 >= self.context_size:
            raise ValueError('Limites de resumo/resolução não cabem no contexto.')
        if self.llm_backend == 'cpu' and self.n_gpu_layers != 0:
            raise ValueError('Perfil CPU exige N_GPU_LAYERS=0.')
        if self.llm_backend == 'cuda' and self.n_gpu_layers == 0:
            raise ValueError('Perfil CUDA exige offload positivo ou -1; escolha CPU explicitamente.')
        self.root = self.root.resolve()
        for name in ('models_dir', 'chroma_persist_dir'):
            value = getattr(self, name)
            setattr(self, name, value.resolve() if value.is_absolute() else self.root / value)
        return self

    @property
    def catalog_path(self):
        return self.chroma_persist_dir.parent / 'catalog.sqlite3'

    @property
    def fingerprint(self):
        values = {key: getattr(self, key) for key in (
            'embedding_model_name', 'embedding_model_revision', 'embedding_max_tokens',
            'chunk_size_chars', 'chunk_overlap_chars')}
        values.update(normalization='L2', text_processing='unicode-NFC-newlines-v1', dimension=1024)
        return sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def load_settings(profile=None, **overrides):
    if profile == 'cpu':
        overrides.update(llm_backend='cpu', embedding_device='cpu', n_gpu_layers=0)
    return Settings(**overrides)
