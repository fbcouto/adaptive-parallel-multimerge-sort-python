import csv
import random
import time
import sys
import numpy as np

try:
    import rust_multimerge
except ImportError:
    print("[ERRO] rust_multimerge não encontrado. Ative o .venv e rode maturin develop.")
    sys.exit(1)

def gerar_padrao_serra_numpy(arr, dentes):
    n = len(arr)
    tamanho_chunk = n // dentes
    if tamanho_chunk <= 1:
        return
    for d in range(dentes):
        if d % 2 == 1:
            inicio = d * tamanho_chunk
            fim = min(inicio + tamanho_chunk, n)
            arr[inicio:fim] = arr[inicio:fim][::-1]

def benchmark_python_numpy(np_array):
    inicio = time.perf_counter()
    np_array.sort(kind='quicksort') 
    fim = time.perf_counter()
    return int((fim - inicio) * 1000)

def benchmark_rust_numeros(np_array):
    inicio = time.perf_counter()
    rust_multimerge.multi_merge_rust(np_array.data)
    fim = time.perf_counter()
    return int((fim - inicio) * 1000)

def gerar_lista_quantidades():
    return [1_000_000, 5_000_000]

def exibir_comparacao(cenario, t_nativo, t_multi):
    if t_multi > 0:
        ratio = t_nativo / t_multi
        ganho = f"{ratio:.2f}x mais rápido" if ratio >= 1 else f"{1/ratio:.2f}x mais lento"
    else:
        ganho = "N/A (Tempo Rust próximo de 0ms)"
    print(f"  ↳ [{cenario}] Nativo: {t_nativo}ms | MultiMerge: {t_multi}ms ➔ Rust foi {ganho}")

def main():
    nome_arquivo = "resultados_benchmarks_python_numeros_corrigido.csv"
    quantidades = gerar_lista_quantidades()
    DENTES = 1000

    print(f"🚀 Iniciando Benchmark Numérico Focado (1M e 5M)...")

    with open(nome_arquivo, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Quantidade", "ordNativo", "invordNativo", "serraNativo", "aleNativo", 
                         "ordMulti", "invordMulti", "serraMulti", "aleMulti"])
        
        for n in quantidades:
            print(f"\n📊 TESTANDO ESCALA: {n:,} Elementos")
            
            # --- 1. CENÁRIO: ALEATÓRIO ---
            np.random.seed(42)
            arr_aleatorio_py = np.random.randint(-100_000_000, 100_000_000, size=n, dtype=np.int32)
            arr_aleatorio_rs = arr_aleatorio_py.copy()
            
            t_ale_nat = benchmark_python_numpy(arr_aleatorio_py)
            t_ale_mul = benchmark_rust_numeros(arr_aleatorio_rs)
            exibir_comparacao("ALEATÓRIO", t_ale_nat, t_ale_mul)
            
            # --- EXTRAÇÃO DA BASE ORDENADA ---
            arr_ordenado_py = arr_aleatorio_rs.copy()
            arr_ordenado_rs = arr_aleatorio_rs.copy()
            
            # --- 2. CENÁRIO: ORDENADO ---
            t_ord_nat = benchmark_python_numpy(arr_ordenado_py)
            t_ord_mul = benchmark_rust_numeros(arr_ordenado_rs)
            exibir_comparacao("ORDENADO", t_ord_nat, t_ord_mul)
            
            # --- 3. CENÁRIO: INVERTIDO ---
            # Corrigido: Nomeando corretamente como arr_invertido para bater com a validação
            arr_invertido_py = arr_ordenado_rs[::-1].copy()
            arr_invertido_rs = arr_invertido_py.copy()
            
            t_inv_nat = benchmark_python_numpy(arr_invertido_py)
            t_inv_mul = benchmark_rust_numeros(arr_invertido_rs)
            exibir_comparacao("INVERTIDO", t_inv_nat, t_inv_mul)
            
            # --- 4. CENÁRIO: SERRA ---
            arr_serra_py = arr_ordenado_rs.copy()
            gerar_padrao_serra_numpy(arr_serra_py, DENTES)
            arr_serra_rs = arr_serra_py.copy()
            
            t_ser_nat = benchmark_python_numpy(arr_serra_py)
            t_ser_mul = benchmark_rust_numeros(arr_serra_rs)
            exibir_comparacao("SERRA (DENTES)", t_ser_nat, t_ser_mul)
            
            # --- VALIDAÇÃO ---
            if (not np.array_equal(arr_ordenado_py, arr_ordenado_rs) or
                not np.array_equal(arr_invertido_py, arr_invertido_rs) or
                not np.array_equal(arr_serra_py, arr_serra_rs) or
                not np.array_equal(arr_aleatorio_py, arr_aleatorio_rs)):
                print(f"\n[ERRO CRÍTICO] Divergência na ordenação numérica detectada no tamanho: {n}")
                sys.exit(1)
            
            writer.writerow([n, t_ord_nat, t_inv_nat, t_ser_nat, t_ale_nat, 
                             t_ord_mul, t_inv_mul, t_ser_mul, t_ale_mul])
            file.flush()
            
            del arr_aleatorio_py, arr_aleatorio_rs, arr_ordenado_py, arr_ordenado_rs
            del arr_invertido_py, arr_invertido_rs, arr_serra_py, arr_serra_rs

    print(f"\n[SUCESSO] Relatório '{nome_arquivo}' gerado com sucesso!")

if __name__ == "__main__":
    main()