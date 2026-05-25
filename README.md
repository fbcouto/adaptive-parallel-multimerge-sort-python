# 🚀 Adaptive Parallel Multimerge Sort (Python Native Extension)

This repository contains the native Python extension wrapper for the **Multimerge** parallel sorting algorithm.

By leveraging **PyO3** and **Maturin**, the core Rust engine is compiled into a high-performance Dynamic Link Library (`.dll` / `.pyd` on Windows), allowing Python scripts to offload intensive sorting workloads to multi-threaded hardware with absolute zero-copy memory overhead.

---

# 🔗 Core Algorithm & Academic Background

> 📌 **Note:** The mathematical foundations, dynamic heuristics, and exhaustive standalone benchmarks of the Multimerge engine are fully detailed and tested in the primary repository:
>
> 👉 **[Core Multimerge Sorting Repository](https://github.com/fbcouto/adaptive-parallel-multimerge-sort)**
The core theoretical foundation of this parallel architecture is based on the original research and paper:

- Title: Multimerge
- Authors: Fernando B. Couto & Fábio S. Couto
- Conference: PDPTA'11 — The 2011 International Conference on Parallel and Distributed Processing Techniques and Applications
- Lecture Series: WorldComp'11 (The 2011 World Congress in Computer Science, Computer Engineering, and Applied Computing)
- The architecture implements a hybrid processing model based on the original *Multimerge* paper published in **PDPTA'11** (The 2011 International Conference on Parallel and Distributed Processing Techniques and Applications).

It modernizes those multi-merge paradigms by utilizing runtime entropy sampling (an Adaptive Oscillation Heuristic) and Rayon's work-stealing parallel scheduler.

---

# 🛠️ Compilation & DLL Generation Guide

To bridge the gap between Python and Rust, the project compiles the codebase into a native CPython extension module (`rust_multimerge`).

## 1. Prerequisites

Ensure your local environment has the following toolchains installed:

- **Rust Toolchain:** Stable channel (`cargo`, `rustc >= 1.70`)
- **Python:** Version `3.12` (matching your current execution layout)

---

## 2. Layout Structure

```text
multimerge-Python-dll/
├── Cargo.toml                  # Rust compilation manifest
├── pyproject.toml              # Maturin build system metadata
├── gerar_csv_python_numeros.py # Automated integer testbed
├── gerar_csv_python_texto.py   # Automated string testbed
└── src/
    └── lib.rs                  # PyO3 Bindings + Core Algorithm
```

---

## 3. Step-by-Step Building Process

Open your PowerShell or Terminal inside the `multimerge-Python-dll` folder and run the following commands:

```powershell
# 1. Create a local virtual environment
python -m venv .venv

# 2. Activate the isolated environment
.\.venv\Scripts\Activate.ps1

# 3. Install build requirements (NumPy is required by the benchmarking testbed)
pip install maturin numpy

# 4. Compile the Rust crate and inject the native extension directly into Python
maturin develop --release
```

---

## 4. Behind the Scenes: DLL Mappings

When `maturin develop --release` executes:

1. It reads `Cargo.toml` and triggers a release-tier compilation (`opt-level = 3`) via Cargo.
2. It generates a standardized dynamic library link file (`rust_multimerge.dll`).
3. For Windows environments, it maps this binary module into a `.pyd` Python Extension DLL file called:
   `rust_multimerge.cp312-win_amd64.pyd`
4. PyO3 hooks the C-callable bindings, exposing `multi_merge_rust` and `multi_merge_rust_strings` to the Python interpreter runtime.

---

# 🧪 Benchmark Results (Empirical Data)

The following metrics represent the real-world execution profiles captured directly from the compiled native extension running against CPython/NumPy core architectures.

---

## 🔢 1. Numeric Testbed Evaluation (int32 Array Buffers)

**Framework:** NumPy Array Pointer Sharing vs. Multimerge i32 Buffer Hooking  
**Data Scale:** 1,000,000 and 5,000,000 elements

| Vector Size | Scenario Profile | NumPy Nativo (C-Quicksort) | Multimerge (Rust Engine) | Performance Factor |
|---|---|---|---|---|
| 1,000,000 | RANDOM | 14 ms | 9 ms | 🚀 1.55x Faster |
| 1,000,000 | SORTED | 14 ms | 0 ms | 🚀 Near-instant early exit |
| 1,000,000 | REVERSED | 14 ms | 1 ms | 🚀 14.00x Faster |
| 1,000,000 | SAWTOOTH PATTERN | 11 ms | 12 ms | ⚙️ 1.09x Latency Parity |
| 5,000,000 | RANDOM | 76 ms | 43 ms | 🚀 1.77x Faster |
| 5,000,000 | SORTED | 77 ms | 2 ms | 🚀 38.50x Faster |
| 5,000,000 | REVERSED | 81 ms | 5 ms | 🚀 16.20x Faster |
| 5,000,000 | SAWTOOTH PATTERN | 93 ms | 24 ms | 🚀 3.88x Faster |

---

## 🔤 2. Textual Testbed Evaluation (String / 6-byte Flat Buffers)

**Framework:** Fixed-width S6 NumPy View vs. Zero-Copy bytearray Pointer Translation  
**Data Scale:** 1,000,000 and 5,000,000 string chunks

| Vector Size | Scenario Profile | C-NumPy View (S6) | Multimerge (Rust Engine) | Performance Factor |
|---|---|---|---|---|
| 1,000,000 | RANDOM | 148 ms | 18 ms | 🚀 8.22x Faster |
| 1,000,000 | SORTED | 51 ms | 7 ms | 🚀 7.29x Faster |
| 1,000,000 | REVERSED | 85 ms | 9 ms | 🚀 9.44x Faster |
| 1,000,000 | SAWTOOTH PATTERN | 67 ms | 79 ms | ⚙️ 1.18x Latency Parity |
| 5,000,000 | RANDOM | 814 ms | 94 ms | 🚀 8.66x Faster |
| 5,000,000 | SORTED | 297 ms | 37 ms | 🚀 8.03x Faster |
| 5,000,000 | REVERSED  | 501 ms | 51 ms | 🚀 9.82x Faster |
| 5,000,000 | SAWTOOTH PATTERN | 394 ms | 94 ms | 🚀 4.19x Faster |

---

# 💻 Reusable Script Integration Example

Other Python programs can utilize the compiled library functions directly by interacting with standard memory-contiguous buffers:

```python
import rust_multimerge
import numpy as np

# Integer Array In-Place Mutation (Zero-Copy)
num_data = np.array([5, 1, 9, -3, 2], dtype=np.int32)
rust_multimerge.multi_merge_rust(num_data.data)
print(num_data)  # Output: [-3, 1, 2, 5, 9]

# 6-Byte Block String In-Place Mutation
text_payload = bytearray(b"FOO000BAR000AAA000")  # 3 chunks of 6 bytes
rust_multimerge.multi_merge_rust_strings(text_payload)
print(text_payload)  # Output ordered memory blocks: b"AAA000BAR000FOO000"
```

---

# 📄 License

This project is licensed under the Apache License 2.0.

You may obtain a copy of the license at:

- https://www.apache.org/licenses/LICENSE-2.0

Copyright © Fernando B. Couto

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this project except in compliance with the License.
You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
