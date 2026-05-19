use std::time::Instant;
use rayon::prelude::*;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyByteArray};
use pyo3::buffer::PyBuffer;

// ==========================================
// 1. UTILITÁRIOS GENÉRICOS
// ==========================================

fn calcular_minrun(mut n: usize) -> usize {
    let mut r = 0;
    while n >= 64 {
        r |= n & 1;
        n >>= 1;
    }
    n + r
}

fn insertion_sort<T: Ord>(arr: &mut [T]) {
    for i in 1..arr.len() {
        let mut j = i;
        while j > 0 && arr[j - 1] > arr[j] {
            arr.swap(j - 1, j);
            j -= 1;
        }
    }
}

fn detectar_tendencia_global<T: Ord>(arr: &mut [T]) -> bool {
    let n = arr.len();
    if n <= 1 { return true; }

    let mut ordenado = true;
    for i in 0..n - 1 {
        if arr[i] > arr[i + 1] {
            ordenado = false;
            break;
        }
    }
    if ordenado { return true; }

    let mut invertido = true;
    for i in 0..n - 1 {
        if arr[i] < arr[i + 1] {
            invertido = false;
            break;
        }
    }
    if invertido {
        arr.reverse();
        return true;
    }
    false
}

// ==========================================
// 2. MAPEAMENTO E MERGE ESTÁVEL
// ==========================================

fn mapear_particao_timsort<T: Ord + Clone>(chunk: &mut [T], minrun: usize) -> Vec<usize> {
    let n = chunk.len();
    if n == 0 { return vec![]; }
    let mut runs = Vec::new();
    let mut i = 0;

    while i < n {
        let mut run_len = 1;
        if i + 1 < n {
            let crescente = chunk[i] <= chunk[i + 1];
            run_len += 1;
            while i + run_len < n {
                if (chunk[i + run_len - 1] <= chunk[i + run_len]) == crescente {
                    run_len += 1;
                } else { break; }
            }
            if !crescente { chunk[i..i + run_len].reverse(); }
        }
        
        if run_len < minrun && i + run_len < n {
            let force_len = std::cmp::min(minrun, n - i);
            insertion_sort(&mut chunk[i..i + force_len]);
            run_len = force_len;
        }
        runs.push(run_len);
        i += run_len;
    }
    runs
}

fn mesclar_estavel<T: Ord + Clone>(arr: &mut [T], mid: usize, buffer: &mut [T]) {
    let n = arr.len();
    if n <= 1 || arr[mid - 1] <= arr[mid] { return; }

    for i in 0..mid {
        buffer[i] = arr[i].clone();
    }

    let (mut i, mut j, mut k) = (0, mid, 0);

    while i < mid && j < n {
        if buffer[i] <= arr[j] {
            arr[k] = buffer[i].clone();
            i += 1;
        } else {
            arr[k] = arr[j].clone();
            j += 1;
        }
        k += 1;
    }

    while i < mid {
        arr[k] = buffer[i].clone();
        i += 1;
        k += 1;
    }
}

// ==========================================
// 3. RECURSÃO PARALELA GENÉRICA
// ==========================================

fn sort_recursivo_paralelo<T: Ord + Clone + Send>(arr: &mut [T], buffer: &mut [T], threshold: usize) {
    let n = arr.len();
    if n <= threshold {
        ordenar_sequencial_timsort_style(arr);
        return;
    }

    let mid = n / 2;
    let (left, right) = arr.split_at_mut(mid);
    let (buf_left, buf_right) = buffer.split_at_mut(mid);

    rayon::join(
        || sort_recursivo_paralelo(left, buf_left, threshold),
        || sort_recursivo_paralelo(right, buf_right, threshold)
    );

    mesclar_estavel(arr, mid, buffer);
}

fn ordenar_sequencial_timsort_style<T: Ord + Clone>(arr: &mut [T]) {
    let n = arr.len();
    if n <= 1 { return; }
    
    let mut buffer = vec![arr[0].clone(); n];
    let minrun = calcular_minrun(n);
    let indices = mapear_particao_timsort(arr, minrun);
    
    let mut pilha: Vec<(usize, usize)> = Vec::new();
    let mut ptr = 0;
    
    for size in indices {
        pilha.push((ptr, size));
        ptr += size;
        
        while pilha.len() > 1 {
            let i = pilha.len();
            if pilha[i-2].1 <= pilha[i-1].1 {
                let (s2, l2) = pilha.pop().unwrap();
                let (s1, l1) = pilha.pop().unwrap();
                mesclar_simples(arr, s1, l1, s2, l2, &mut buffer);
                pilha.push((s1, l1 + l2));
            } else { break; }
        }
    }
    
    while pilha.len() > 1 {
        let (s2, l2) = pilha.pop().unwrap();
        let (s1, l1) = pilha.pop().unwrap();
        mesclar_simples(arr, s1, l1, s2, l2, &mut buffer);
        pilha.push((s1, l1 + l2));
    }
}

fn mesclar_simples<T: Ord + Clone>(arr: &mut [T], s1: usize, l1: usize, s2: usize, l2: usize, buf: &mut [T]) {
    if arr[s1 + l1 - 1] <= arr[s2] { return; }

    for i in 0..l1 {
        buf[i] = arr[s1 + i].clone();
    }

    let (mut b_idx, mut r_idx, mut out_idx) = (0, s2, s1);
    let r_end = s2 + l2;

    while b_idx < l1 && r_idx < r_end {
        if buf[b_idx] <= arr[r_idx] {
            arr[out_idx] = buf[b_idx].clone();
            b_idx += 1;
        } else {
            arr[out_idx] = arr[r_idx].clone();
            r_idx += 1;
        }
        out_idx += 1;
    }

    while b_idx < l1 {
        arr[out_idx] = buf[b_idx].clone();
        b_idx += 1;
        out_idx += 1;
    }
}

pub fn ordenar_multi_merge<T: Ord + Clone + Send>(arr: &mut [T]) {
    let n = arr.len();
    if n < 1024 {
        insertion_sort(arr);
        return;
    }
    
    // 1. O seu algoritmo base avalia as pontas e o meio. 
    // Se estiver ordenado ou inverso, mata o problema em O(n) imediatamente.
    if detectar_tendencia_global(arr) { return; }

    // 2. HEURÍSTICA DE OSCILAÇÃO (Detecção Real de Caos)
    let mut e_caos_puro = false;
    if n > 120 {
        let mid = n / 2;
        let mut mudancas_direcao = 0;
        let mut subindo = arr[mid] <= arr[mid + 1];
        
        // Analisa uma janela de 100 elementos no coração do array
        for i in (mid + 1)..(mid + 100).min(n - 1) {
            let direcao_atual = arr[i] <= arr[i + 1];
            if direcao_atual != subindo {
                mudancas_direcao += 1;
                subindo = direcao_atual;
            }
        }
        
        // Se a tendência mudar mais de 15 vezes em 100 elementos, é ruído/caos puro.
        if mudancas_direcao > 15 {
            e_caos_puro = true;
        }
    }

    if !e_caos_puro {
        // ROTA A: O seu algoritmo original estável (TimSort + Merge) devora os dentes de serra
        let mut buffer = vec![arr[0].clone(); n];
        let num_threads = rayon::current_num_threads();
        let threshold = (n / num_threads).max(1_000_000); 
        sort_recursivo_paralelo(arr, &mut buffer, threshold);
    } else {
        // ROTA B: O BlockQuicksort paralelo do Rayon assume o controle e tritura o caos in-place
        arr.par_sort_unstable();
    }
}
// ==========================================
// 4. CAMADA DE INTERFACE PYTHON (ALINHAMENTO DE TIPOS)
// ==========================================

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct StringFixa([u8; 6]);
unsafe impl Send for StringFixa {}

// Função 1: Números Otimizados (Requisita explicitamente o formato i32)
#[pyfunction]
fn multi_merge_rust(obj: &PyAny) -> PyResult<()> {
    // Casamento perfeito: pede ao NumPy o buffer no formato original i32
    let buffer = pyo3::buffer::PyBuffer::<i32>::get(obj)?;

    if !buffer.is_c_contiguous() {
        return Err(pyo3::exceptions::PyValueError::new_err("O buffer precisa ser contíguo (C-contiguous)"));
    }

    let ptr = buffer.buf_ptr();
    let len_bytes = buffer.len_bytes();

    // Mapeia os ponteiros diretamente para a nossa fatia mutável
    let slice_i32: &mut [i32] = unsafe {
        std::slice::from_raw_parts_mut(
            ptr as *mut i32,
            len_bytes / std::mem::size_of::<i32>(),
        )
    };

    ordenar_multi_merge(slice_i32);

    Ok(())
}

// Função 2: Texto Otimizado (Mapeado via u8 porque representamos bytes textuais)
#[pyfunction]
fn multi_merge_rust_strings(obj: &PyAny) -> PyResult<()> {
    // Como no Python usamos um bytearray() para o texto, o tipo nativo dele é u8
    let buffer = pyo3::buffer::PyBuffer::<u8>::get(obj)?;

    if !buffer.is_c_contiguous() {
        return Err(pyo3::exceptions::PyValueError::new_err("O buffer precisa ser contíguo"));
    }

    let ptr = buffer.buf_ptr();
    let len_bytes = buffer.len_bytes();

    let slice_u8: &mut [u8] = unsafe {
        std::slice::from_raw_parts_mut(ptr as *mut u8, len_bytes)
    };

    let mut vetor_strings: Vec<StringFixa> = slice_u8
        .chunks_exact(6)
        .map(|chunk| {
            let mut bytes = [0u8; 6];
            bytes.copy_from_slice(chunk);
            StringFixa(bytes)
        })
        .collect();

    ordenar_multi_merge(&mut vetor_strings);

    for (i, string_fixa) in vetor_strings.iter().enumerate() {
        let idx = i * 6;
        slice_u8[idx..idx + 6].copy_from_slice(&string_fixa.0);
    }

    Ok(())
}

// Registro das funções (Permanece igual)
#[pymodule]
fn rust_multimerge(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(multi_merge_rust, m)?)?;
    m.add_function(wrap_pyfunction!(multi_merge_rust_strings, m)?)?;
    Ok(())
}