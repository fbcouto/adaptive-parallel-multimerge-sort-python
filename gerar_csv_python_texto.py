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

def gerar_flat_bytes_aleatorios(n):
    charset = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    flat = bytearray(n * 6)
    random.seed(42)
    for i in range(n):
        comprimento = random.randint(3, 6)
        idx_base = i * 6
        for j in range(comprimento):
            flat[idx_base + j] = random.choice(charset)
    return flat

def inverter_flat_bytes(orig):
    n = len(orig) // 6
    inv = bytearray(len(orig))
    for i in range(n):
        inv[(n - 1 - i) * 6 : (n - i) * 6] = orig[i * 6 : (i + 1) * 6]
    return inv

def aplicar_padrao_serra_nos_bytes(orig, dentes):
    serra = bytearray(orig)
    n = len(serra) // 6
    tamanho_chunk = n // dentes
    if tamanho_chunk <= 1:
        return serra
    for d in range(dentes):
        if d % 2 == 1:
            inicio = d * tamanho_chunk
            fim = min(inicio + tamanho_chunk, n)
            for i in range((fim - inicio) // 2):
                idx1 = (inicio + i) * 6
                idx2 = (fim - 1 - i) * 6
                temp = serra[idx1 : idx1 + 6]
                serra[idx1 : idx1 + 6] = serra[idx2 : idx2 + 6]
                serra[idx2 : idx2 + 6] = temp
    return serra

def benchmark_python_numpy(flat_bytes):
    np_view = np.frombuffer(flat_bytes, dtype='S6')
    inicio = time.perf_counter()
    np_view.sort(kind='quicksort') 
    fim = time.perf_counter()
    return int((fim - inicio) * 1000)

def benchmark_rust_string(flat_bytes):
    inicio = time.perf_counter()
    rust_multimerge.multi_merge_rust_strings(flat_bytes)
    fim = time.perf_counter()
    return int((fim - inicio) * 1000)

def gerar_lista_quantidades():
    # MODIFICADO: Foco exclusivo em 1 Milhão e 5 Milhões
    return [1_000_000, 5_000_000]

def exibir_comparacao(cenario, t_nativo, t_multi):
    if t_multi > 0:
        ratio = t_nativo / t_multi
        ganho = f"{ratio:.2f}x mais rápido" if ratio >= 1 else f"{1/ratio:.2f}x mais lento"
    else:
        ganho = "N/A"
    print(f"  ↳ [{cenario}] Nativo: {t_nativo}ms | MultiMerge: {t_multi}ms ➔ Rust foi {ganho}")

def main():
    nome_arquivo = "resultados_benchmarks_python_texto.csv"
    quantidades = gerar_lista_quantidades()
    DENTES = 1000 

    print(f"🚀 Iniciando Benchmark de Texto Focado (1M e 5M)...")

    with open(nome_arquivo, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Quantidade", "ordNativo", "invordNativo", "serraNativo", "aleNativo", 
                         "ordMulti", "invordMulti", "serraMulti", "aleMulti"])
        
        for n in quantidades:
            print(f"\n📝 TESTANDO ESCALA: {n:,} Strings (6 bytes)")
            
            # --- 1. CENÁRIO: ALEATÓRIO ---
            bytes_aleatorio_py = gerar_flat_bytes_aleatorios(n)
            bytes_aleatorio_rs = bytearray(bytes_aleatorio_py)
            
            t_ale_nat = benchmark_python_numpy(bytes_aleatorio_py)
            t_ale_mul = benchmark_rust_string(bytes_aleatorio_rs)
            exibir_comparacao("ALEATÓRIO", t_ale_nat, t_ale_mul)
            
            # --- EXTRAÇÃO DA BASE ORDENADA ESTÁVEL ---
            bytes_ordenado_py = bytearray(bytes_aleatorio_rs)
            bytes_ordenado_rs = bytearray(bytes_aleatorio_rs)
            
            # --- 2. CENÁRIO: ORDENADO ---
            t_ord_nat = benchmark_python_numpy(bytes_ordenado_py)
            t_ord_mul = benchmark_rust_string(bytes_ordenado_rs)
            exibir_comparacao("ORDENADO", t_ord_nat, t_ord_mul)
            
            # --- 3. CENÁRIO: INVERTIDO ---
            bytes_invertido_py = inverter_flat_bytes(bytes_ordenado_rs)
            bytes_invertido_rs = bytearray(bytes_invertido_py)
            
            t_inv_nat = benchmark_python_numpy(bytes_invertido_py)
            t_inv_mul = benchmark_rust_string(bytes_invertido_rs)
            exibir_comparacao("INVERTIDO", t_inv_nat, t_inv_mul)
            
            # --- 4. CENÁRIO: SERRA ---
            bytes_serra_py = aplicar_padrao_serra_nos_bytes(bytes_ordenado_rs, DENTES)
            bytes_serra_rs = bytearray(bytes_serra_py)
            
            t_ser_nat = benchmark_python_numpy(bytes_serra_py)
            t_ser_mul = benchmark_rust_string(bytes_serra_rs)
            exibir_comparacao("SERRA (DENTES)", t_ser_nat, t_ser_mul)
            
            writer.writerow([n, t_ord_nat, t_inv_nat, t_ser_nat, t_ale_nat, 
                             t_ord_mul, t_inv_mul, t_ser_mul, t_ale_mul])
            file.flush()
            
            del bytes_aleatorio_py, bytes_aleatorio_rs, bytes_ordenado_py, bytes_ordenado_rs
            del bytes_invertido_py, bytes_invertido_rs, bytes_serra_py, bytes_serra_rs

    print(f"\n[SUCESSO] Relatório '{nome_arquivo}' gerado!")

if __name__ == "__main__":
    main()