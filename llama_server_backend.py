"""llama-server 子进程后端 — 替代 llama-cpp-python 进程内加载。

对外提供与 llama-cpp-python `Llama` 对象兼容的 `create_chat_completion`，
内部通过 llama-server 的 OpenAI 兼容 HTTP 接口推理，进程隔离、跑完即停。

依赖 install_runtime.py 生成的 runtime_config.json（由 llama.cpp b10436 预编译
二进制 + SHA256 校验安装），不再需要安装 llama-cpp-python。
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

NODE_ROOT = Path(__file__).resolve().parent
RUNTIME_CONFIG_PATH = NODE_ROOT / "runtime_config.json"
LLAMA_SEED_MODULUS = 0xFFFFFFFF
SERVER_ALIAS = "comfyui-local"
API_KEY = "comfyui-local"


def normalize_llama_seed(seed: int) -> int:
    """把 ComfyUI 的 uint64 seed 映射到 llama.cpp 的 uint32 范围。"""
    return int(seed) % LLAMA_SEED_MODULUS


@dataclass(frozen=True)
class RuntimeSpec:
    executable: Path
    library_dirs: tuple[Path, ...]
    platform_name: str
    backend: str
    device: str | None = None


def _installer_name() -> str:
    return "install_runtime.py"


def _configured_path(root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Invalid {label} in {RUNTIME_CONFIG_PATH.name}")
    path = (root / Path(value)).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError(
            f"{label} must remain inside the custom node directory: {path}"
        ) from error
    return path


def load_runtime_spec(root: Path = NODE_ROOT) -> RuntimeSpec:
    """读取 install_runtime.py 生成的 runtime_config.json。"""
    config_path = root / RUNTIME_CONFIG_PATH.name
    if not config_path.is_file():
        raise RuntimeError(
            f"llama.cpp runtime 尚未安装。请先在节点目录执行 {_installer_name()}，"
            f"然后重启 ComfyUI。"
        )
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"无法读取 {config_path}，请重新运行 {_installer_name()} --force。"
        ) from error

    if config.get("schema_version") != 1:
        raise RuntimeError(
            f"runtime 配置版本不受支持，请重新运行 {_installer_name()} --force。"
        )
    active_platform = _normalize_platform()
    configured_platform = config.get("platform")
    if configured_platform != active_platform:
        raise RuntimeError(
            f"runtime 配置是为 {configured_platform} 准备的，但当前运行在 "
            f"{active_platform}。请重新运行 {_installer_name()} --force。"
        )

    executable = _configured_path(root, config.get("executable"), "executable")
    raw_library_dirs = config.get("library_dirs", [])
    if not isinstance(raw_library_dirs, list):
        raise RuntimeError(f"Invalid library_dirs in {config_path}")
    library_dirs = tuple(
        _configured_path(root, value, "library directory")
        for value in raw_library_dirs
    )
    raw_device = (config.get("runtime_options") or {}).get("device")
    device = str(raw_device) if raw_device is not None else None
    return RuntimeSpec(
        executable=executable,
        library_dirs=library_dirs or (executable.parent,),
        platform_name=active_platform,
        backend=str(config.get("backend", "unknown")),
        device=device,
    )


def runtime_is_installed(root: Path = NODE_ROOT) -> bool:
    """是否已通过 install_runtime.py 安装过 llama-server 运行时。"""
    return (root / RUNTIME_CONFIG_PATH.name).is_file()


def _normalize_platform(system_name: str | None = None) -> str:
    import platform

    value = (system_name or platform.system()).strip().casefold()
    names = {
        "windows": "windows",
        "linux": "linux",
        "darwin": "macos",
        "macos": "macos",
    }
    if value not in names:
        raise RuntimeError(
            f"Unsupported operating system: {system_name or platform.system()}"
        )
    return names[value]


def build_runtime_environment(
    runtime_spec: RuntimeSpec,
    base_environment: dict[str, str] | None = None,
) -> dict[str, str]:
    environment = dict(os.environ if base_environment is None else base_environment)
    library_path = os.pathsep.join(str(path) for path in runtime_spec.library_dirs)
    environment["PATH"] = library_path + os.pathsep + environment.get("PATH", "")
    if runtime_spec.platform_name == "linux":
        environment["LD_LIBRARY_PATH"] = (
            library_path + os.pathsep + environment.get("LD_LIBRARY_PATH", "")
        )
    elif runtime_spec.platform_name == "macos":
        environment["DYLD_LIBRARY_PATH"] = (
            library_path + os.pathsep + environment.get("DYLD_LIBRARY_PATH", "")
        )
    return environment


def _comfy_gpu_name() -> str | None:
    """获取 ComfyUI (torch) 当前使用的 GPU 名称，用于自动匹配 llama.cpp 设备。"""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(torch.cuda.current_device()) or None
    except Exception:
        pass
    return None


def _run_list_devices(
    executable: Path,
    env: dict[str, str],
    platform_name: str,
) -> str | None:
    """跑 llama-server --list-devices，返回输出文本。"""
    process_options = {}
    if platform_name == "windows":
        process_options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            [str(executable), "--list-devices"],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            **process_options,
        )
        return (proc.stdout or "") + "\n" + (proc.stderr or "")
    except Exception:
        return None


def _parse_devices(output: str) -> list[tuple[str, str]]:
    """解析 --list-devices 输出，返回 [(设备名, 名称), ...]（如 [('ROCm0', 'AMD ...'), ...]）。"""
    devices = []
    for line in output.splitlines():
        m = re.search(r"^\s*(\S+)\s*[:：]\s*(.+)$", line)
        if m:
            devices.append((m.group(1), m.group(2).strip()))
    return devices


def _is_integrated_gpu(label: str) -> bool:
    """判断 GPU 名称是否为核显（名称含 Graphics/Integrated/UHD/Iris 等）。"""
    low = label.casefold()
    return any(k in low for k in ("graphics", "integrated", "uhd", "iris"))


def _auto_resolve_device(
    executable: Path,
    env: dict[str, str],
    platform_name: str,
    gpu_name: str | None,
) -> str | None:
    """跑 --list-devices，优先匹配 torch GPU 名称；核显则改选独显。"""
    if not gpu_name:
        return None
    output = _run_list_devices(executable, env, platform_name)
    if not output:
        return None
    devices = _parse_devices(output)
    if not devices:
        return None

    target = gpu_name.casefold()
    tokens = [t for t in re.findall(r"\d+", gpu_name) if len(t) >= 3]

    matched = None
    for dev_name, dev_label in devices:
        low = dev_label.casefold()
        if target in low or low in target or any(t in dev_label for t in tokens):
            matched = (dev_name, dev_label)
            break

    # 匹配到核显时，改选第一个非核显（独显）
    if matched is not None and _is_integrated_gpu(matched[1]):
        for dev_name, dev_label in devices:
            if not _is_integrated_gpu(dev_label):
                return dev_name

    # 名称没匹配上时，直接选第一个非核显
    if matched is None:
        for dev_name, dev_label in devices:
            if not _is_integrated_gpu(dev_label):
                return dev_name

    return matched[0] if matched else None


def _resolve_device_name_by_index(
    executable: Path,
    env: dict[str, str],
    platform_name: str,
    index: int,
) -> str | None:
    """按索引返回 llama.cpp 设备名（如第 1 个设备 → ROCm1）。"""
    output = _run_list_devices(executable, env, platform_name)
    if not output:
        return None
    devices = _parse_devices(output)
    if 0 <= index < len(devices):
        return devices[index][0]
    return None


# llama-cpp-python create_chat_completion 参数 → llama-server OpenAI API 参数
_SAMPLER_PARAM_MAP = {
    "max_tokens": "max_tokens",
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "min_p": "min_p",
    "typical_p": "typical_p",
    "repeat_penalty": "repeat_penalty",
    "frequency_penalty": "frequency_penalty",
    "present_penalty": "presence_penalty",
    "mirostat_mode": "mirostat",
    "mirostat_eta": "mirostat_eta",
    "mirostat_tau": "mirostat_tau",
}


class LlamaServerBackend:
    """llama-cpp-python `Llama` 对象的进程外替身。

    仅实现编剧链/提示词增强实际用到的接口：
    - create_chat_completion(messages, seed, **params)
    - close()
    并暴露若干兼容属性（n_tokens / _ctx / is_hybrid / _hybrid_cache_mgr），
    保证上游无感。
    """

    def __init__(
        self,
        model_path,
        mmproj_path=None,
        n_ctx: int = 8192,
        n_gpu_layers=-1,
        image_min_tokens: int = 0,
        image_max_tokens: int = 0,
        runtime_spec: RuntimeSpec | None = None,
        device: str | None = None,
    ):
        self.model = Path(model_path)
        self.mmproj = Path(mmproj_path) if mmproj_path else None
        self.n_ctx = int(n_ctx)
        self.n_gpu_layers = n_gpu_layers
        self.image_min_tokens = int(image_min_tokens or 0)
        self.image_max_tokens = int(image_max_tokens or 0)
        self.device = device
        self.runtime_spec = runtime_spec or load_runtime_spec()
        self.executable = self.runtime_spec.executable
        self.root = self.executable.parent
        self.port = self._free_port()
        self.process: subprocess.Popen | None = None
        self.log = None

        # 兼容 llama-cpp-python 的属性（上游个别节点会访问）
        self.n_tokens = 0
        self._ctx = None
        self.is_hybrid = False
        self._hybrid_cache_mgr = None

        self.start()

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _log_tail(self) -> str:
        if self.log is None:
            return ""
        self.log.flush()
        self.log.seek(0)
        return self.log.read().decode("utf-8", errors="replace")[-5000:]

    def start(self, timeout: float = 300.0) -> None:
        if not self.executable.is_file():
            raise FileNotFoundError(
                f"llama.cpp runtime 缺失: {self.executable}。"
                f"请在节点目录执行 {_installer_name()}。"
            )
        self.log = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115
        arguments = [
            str(self.executable),
            "--model",
            str(self.model),
            "--alias",
            SERVER_ALIAS,
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--ctx-size",
            str(self.n_ctx),
            "--parallel",
            "1",
            "--n-gpu-layers",
            str(self.n_gpu_layers),
            "--jinja",
            "--no-webui",
        ]
        if self.mmproj is not None and self.mmproj.is_file():
            arguments.extend(["--mmproj", str(self.mmproj)])
        if self.image_max_tokens > 0:
            arguments.extend(["--image-max-tokens", str(self.image_max_tokens)])
        if self.image_min_tokens > 0:
            arguments.extend(["--image-min-tokens", str(self.image_min_tokens)])

        env = build_runtime_environment(self.runtime_spec)

        # GPU 选择优先级：节点指定 > config 指定 > 自动跟随 ComfyUI
        device = self.device
        if device is None:
            device = self.runtime_spec.device
        if device is None:
            gpu_name = _comfy_gpu_name()
            device = _auto_resolve_device(
                self.executable,
                env,
                self.runtime_spec.platform_name,
                gpu_name,
            )
            if device is None:
                print("[JZL-llama] 警告: 未能自动匹配 ComfyUI GPU，llama-server 将使用默认设备")
            else:
                print(f"[JZL-llama] llama-server 设备：{device}（自动匹配 ComfyUI GPU '{gpu_name}'）")
        if device is not None:
            # 纯数字索引（如节点下拉的 "0"/"1"）→ 转成 llama.cpp 设备名（如 ROCm1）
            if str(device).isdigit():
                resolved = _resolve_device_name_by_index(
                    self.executable,
                    env,
                    self.runtime_spec.platform_name,
                    int(device),
                )
                if resolved:
                    device = resolved
            if device:
                arguments.extend(["--device", str(device)])

        process_options = {}
        if self.runtime_spec.platform_name == "windows":
            process_options["creationflags"] = getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            )
        self.process = subprocess.Popen(
            arguments,
            cwd=self.root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            **process_options,
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"llama-server 在加载模型时退出。\n{self._log_tail()}"
                )
            try:
                self._health_check(timeout=2.0)
                return
            except (OSError, RuntimeError):
                time.sleep(0.25)
        raise TimeoutError(
            f"llama-server 未在 {timeout:.0f} 秒内就绪。\n{self._log_tail()}"
        )

    def _health_check(self, timeout: float = 2.0) -> None:
        request = urllib.request.Request(
            self.base_url + "/health",
            headers={"Authorization": f"Bearer {API_KEY}"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()

    def _request(self, payload: dict, timeout: float = 900.0) -> dict:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/v1/chat/completions",
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"llama-server HTTP {error.code}: {detail}") from error
        except Exception as error:
            tail = self._log_tail()
            raise RuntimeError(
                f"llama-server 请求失败: {error}\n--- llama-server 日志 ---\n{tail}"
            ) from error

    def create_chat_completion(self, messages, seed=0, **params):
        """兼容 llama-cpp-python 的 create_chat_completion 调用。"""
        payload: dict = {"messages": messages}
        if seed is not None:
            payload["seed"] = normalize_llama_seed(seed)
        for src, dst in _SAMPLER_PARAM_MAP.items():
            if src in params and params[src] is not None:
                payload[dst] = params[src]

        response = self._request(payload)
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError("llama-server 未返回任何结果。")
        content = (choices[0].get("message") or {}).get("content") or ""
        usage = response.get("usage") or {}
        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        }

    def close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process = None
        if self.log is not None:
            try:
                self.log.close()
            except Exception:
                pass
            self.log = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
