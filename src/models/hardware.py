import importlib
import importlib.util
import os
from pathlib import Path

_dll_handles = []


def configure_windows_dlls():
    if os.name != 'nt' or _dll_handles:
        return
    spec = importlib.util.find_spec('torch')
    if spec and spec.origin:
        library = Path(spec.origin).parent / 'lib'
        if library.is_dir():
            _dll_handles.append(os.add_dll_directory(str(library)))
            os.environ['PATH'] = str(library) + os.pathsep + os.environ.get('PATH','')


def diagnostic(importer=importlib.import_module):
    configure_windows_dlls()
    result = {'torch_cuda': False, 'llama_gpu_support': False, 'offload_effective': None}
    for module in ('torch', 'llama_cpp'):
        try:
            obj = importer(module)
            if module == 'torch':
                result['torch_cuda'] = bool(obj.cuda.is_available())
                result['torch_version'] = obj.__version__
                result['torch_cuda_version'] = obj.version.cuda
                result['gpu'] = obj.cuda.get_device_name(0) if result['torch_cuda'] else None
            else:
                result['llama_gpu_support'] = bool(obj.llama_supports_gpu_offload())
                result['llama_version'] = obj.__version__
        except (ImportError, OSError, RuntimeError) as error:
            result[module + '_error'] = str(error)
    result['cuda_ready'] = result['torch_cuda'] and result['llama_gpu_support']
    result['note'] = 'Offload efetivo só é verificado durante carregamento. Use --profile cpu se CUDA não estiver disponível.'
    return result


def require_device(settings, component):
    if getattr(settings, 'embedding_device' if component == 'embeddings' else 'llm_backend') == 'cpu':
        return
    report = diagnostic()
    supported = report['torch_cuda'] if component == 'embeddings' else report['llama_gpu_support']
    if not supported:
        raise RuntimeError(f'CUDA indisponível para {component}. Execute setup.ps1 ou escolha --profile cpu. {report}')


import ctypes
import ctypes.util


class nvmlMemory_t(ctypes.Structure):
    _fields_ = [
        ('total', ctypes.c_ulonglong),
        ('free', ctypes.c_ulonglong),
        ('used', ctypes.c_ulonglong),
    ]


class nvmlUtilization_t(ctypes.Structure):
    _fields_ = [
        ('gpu', ctypes.c_uint),
        ('memory', ctypes.c_uint),
    ]


class NvmlClient:
    """Cliente NVML nativo e ultra-leve via ctypes (zero subprocessos, ~7 microssegundos por leitura)."""

    def __init__(self):
        self.available = False
        self.device_name = None
        self.handle = None
        self._nvml = None
        self._mem = nvmlMemory_t()
        self._util = nvmlUtilization_t()
        self._temp = ctypes.c_uint()
        self._init_nvml()

    def _init_nvml(self):
        dll_name = 'nvml.dll' if os.name == 'nt' else (ctypes.util.find_library('nvidia-ml') or 'libnvidia-ml.so.1')
        try:
            self._nvml = ctypes.CDLL(dll_name)
            self._nvml.nvmlInit_v2()
            handle = ctypes.c_void_p()
            self._nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle))
            self.handle = handle
            buf = ctypes.create_string_buffer(96)
            self._nvml.nvmlDeviceGetName(self.handle, buf, 96)
            self.device_name = buf.value.decode('utf-8', errors='ignore')
            self.available = True
        except Exception:
            self.available = False
            self.handle = None
            self._nvml = None

    def get_metrics(self):
        if not self.available or not self.handle:
            return None
        try:
            self._nvml.nvmlDeviceGetMemoryInfo(self.handle, ctypes.byref(self._mem))
            self._nvml.nvmlDeviceGetUtilizationRates(self.handle, ctypes.byref(self._util))
            self._nvml.nvmlDeviceGetTemperature(self.handle, 0, ctypes.byref(self._temp))
            total_mib = int(self._mem.total // (1024 * 1024))
            used_mib = int(self._mem.used // (1024 * 1024))
            percent = round((used_mib / total_mib * 100), 1) if total_mib > 0 else 0.0
            return {
                'gpu_name': self.device_name,
                'gpu_util': int(self._util.gpu),
                'vram_used_mib': used_mib,
                'vram_total_mib': total_mib,
                'vram_percent': percent,
                'gpu_temp_c': int(self._temp.value),
            }
        except Exception:
            return None

    def shutdown(self):
        if self._nvml and self.available:
            try:
                self._nvml.nvmlShutdown()
            except Exception:
                pass
            self.available = False
            self.handle = None
            self._nvml = None


_nvml_client = None
_process = None


def get_nvml_client():
    global _nvml_client
    if _nvml_client is None:
        _nvml_client = NvmlClient()
    return _nvml_client


def get_resource_snapshot() -> dict:
    """Coleta telemetria em tempo real com overhead quase zero (< 0.2ms total)."""
    global _process
    import psutil

    if _process is None:
        _process = psutil.Process()

    cpu_pct = psutil.cpu_percent(interval=None)

    vmem = psutil.virtual_memory()
    ram_used_gb = round((vmem.total - vmem.available) / (1024 ** 3), 1)
    ram_total_gb = round(vmem.total / (1024 ** 3), 1)
    ram_pct = round(vmem.percent, 1)

    try:
        rss_mb = round(_process.memory_info().rss / (1024 ** 2), 1)
    except Exception:
        rss_mb = 0.0

    client = get_nvml_client()
    gpu_metrics = client.get_metrics() if client else None

    if gpu_metrics:
        return {
            'cpu_percent': cpu_pct,
            'ram_used_gb': ram_used_gb,
            'ram_total_gb': ram_total_gb,
            'ram_percent': ram_pct,
            'process_rss_mb': rss_mb,
            'gpu_available': True,
            'gpu_name': gpu_metrics['gpu_name'],
            'gpu_util': gpu_metrics['gpu_util'],
            'vram_used_mib': gpu_metrics['vram_used_mib'],
            'vram_total_mib': gpu_metrics['vram_total_mib'],
            'vram_percent': gpu_metrics['vram_percent'],
            'gpu_temp_c': gpu_metrics['gpu_temp_c'],
        }
    else:
        return {
            'cpu_percent': cpu_pct,
            'ram_used_gb': ram_used_gb,
            'ram_total_gb': ram_total_gb,
            'ram_percent': ram_pct,
            'process_rss_mb': rss_mb,
            'gpu_available': False,
            'gpu_name': 'N/A (CPU)',
            'gpu_util': None,
            'vram_used_mib': None,
            'vram_total_mib': None,
            'vram_percent': None,
            'gpu_temp_c': None,
        }

