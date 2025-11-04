from dataclasses import dataclass
from abc import ABC, abstractmethod
import csv
import os
from pathlib import Path

CONTRACT_FEE = 2000.00
MAX_INSTALLMENTS = 5

# ----------------- Utilidades -----------------
def format_brl(value: float) -> str:
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def leia_int(msg, valido=lambda x: True, erro="Valor inválido. Digite novamente."):
    while True:
        try:
            v = int(input(msg))
            if not valido(v):
                print(erro)
                continue
            return v
        except ValueError:
            print("Entrada inválida. Digite um número inteiro.")

def leia_opcao(msg, opcoes_validas):
    while True:
        v = input(msg).strip()
        if v in opcoes_validas:
            return v
        print(f"Opção inválida. Escolha entre: {', '.join(opcoes_validas)}.")

def get_desktop_path() -> Path:
    """
    Retorna o caminho real da Área de Trabalho.
    No Windows, usa a API do sistema (suporta Desktop redirecionado para OneDrive).
    Em macOS/Linux, usa ~/Desktop.
    """
    try:
        if os.name == "nt":
            import ctypes
            import ctypes.wintypes as wt
            # CSIDL_DESKTOPDIRECTORY = 0x10  (pasta física "Desktop")
            CSIDL_DESKTOPDIRECTORY = 0x10
            buf = ctypes.create_unicode_buffer(wt.MAX_PATH)
            res = ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf)
            if res == 0 and buf.value:
                return Path(buf.value)
        # fallback para POSIX e qualquer exceção
        return Path.home() / "Desktop"
    except Exception:
        return Path.home() / "Desktop"

def ensure_csv_suffix(name: str) -> str:
    name = name.strip()
    if not name:
        return "parcelas_orcamento.csv"
    if not name.lower().endswith(".csv"):
        name += ".csv"
    return name

# ----------------- Modelos -----------------
class Imovel(ABC):
    @abstractmethod
    def calcular_aluguel(self) -> float:
        pass

@dataclass
class Apartamento(Imovel):
    quartos: int = 1
    vagas: int = 0
    tem_criancas: bool = True
    def calcular_aluguel(self) -> float:
        v = 700.0
        if self.quartos == 2:
            v += 200.0
        if self.vagas > 0:
            v += 300.0
        if not self.tem_criancas:
            v *= 0.95
        return round(v, 2)

@dataclass
class Casa(Imovel):
    quartos: int = 1
    vagas: int = 0
    def calcular_aluguel(self) -> float:
        v = 900.0
        if self.quartos == 2:
            v += 250.0
        if self.vagas > 0:
            v += 300.0
        return round(v, 2)

@dataclass
class Estudio(Imovel):
    vagas: int = 0
    def calcular_aluguel(self) -> float:
        v = 1200.0
        if self.vagas == 0:
            return round(v, 2)
        if self.vagas <= 2:
            return round(v + 250.0, 2)
        return round(v + 250.0 + (self.vagas - 2) * 60.0, 2)

@dataclass
class Orcamento:
    imovel: Imovel
    parcelas_contrato: int

    def validar(self):
        if not (1 <= self.parcelas_contrato <= MAX_INSTALLMENTS):
            raise ValueError(f"Parcelas devem estar entre 1 e {MAX_INSTALLMENTS}.")

    def aluguel_mensal(self) -> float:
        return round(self.imovel.calcular_aluguel(), 2)

    def parcela_contrato(self) -> float:
        return round(CONTRACT_FEE / self.parcelas_contrato, 2)

    def gerar_parcelas(self):
        aluguel = self.aluguel_mensal()
        parcela = self.parcela_contrato()
        linhas = []
        for mes in range(1, 13):
            pc = parcela if mes <= self.parcelas_contrato else 0.0
            linhas.append({
                "mes": mes,
                "aluguel": round(aluguel, 2),
                "parcela_contrato": round(pc, 2),
                "total": round(aluguel + pc, 2),
            })
        return linhas

# ----------------- Saída/Resumo -----------------
def print_resumo(orc: Orcamento, linhas):
    aluguel = orc.aluguel_mensal()
    parcela = orc.parcela_contrato()
    print("\n--- RESUMO DO ORÇAMENTO ---")
    print(f"Aluguel mensal: {format_brl(aluguel)}")
    print(f"Taxa de contrato: {format_brl(CONTRACT_FEE)} em {orc.parcelas_contrato}x de {format_brl(parcela)}")
    print(f"Total do 1º mês: {format_brl(aluguel + parcela)}")
    if orc.parcelas_contrato < 12:
        print(f"Total após quitar o contrato: {format_brl(aluguel)}")

    # Preview das 3 primeiras linhas do CSV
    print("\nPrévia (3 primeiros meses):")
    for l in linhas[:3]:
        print(
            f"Mês {l['mes']:>2}: aluguel={format_brl(l['aluguel'])}, "
            f"parcela={format_brl(l['parcela_contrato']) if l['parcela_contrato'] else '—'}, "
            f"total={format_brl(l['total'])}"
        )

# ----------------- Função principal -----------------
def main():
    print("=== Orçamento Imobiliário - CSV Simples ===\n")

    print("Tipo de imóvel:\n1) Apartamento\n2) Casa\n3) Estúdio")
    tipo = leia_opcao("Escolha [1-3]: ", {"1", "2", "3"})

    if tipo == "1":
        quartos = leia_int(
            "Número de quartos (1 ou 2): ",
            valido=lambda q: q in (1, 2),
            erro="Somente 1 ou 2."
        )
        vagas = leia_int(
            "Vagas de garagem: ",
            valido=lambda v: v >= 0,
            erro="Não pode ser negativo."
        )
        tem_criancas = input("Há crianças? [s/n]: ").strip().lower() in {"s", "sim"}
        imovel = Apartamento(quartos=quartos, vagas=vagas, tem_criancas=tem_criancas)

    elif tipo == "2":
        quartos = leia_int(
            "Número de quartos (1 ou 2): ",
            valido=lambda q: q in (1, 2),
            erro="Somente 1 ou 2."
        )
        vagas = leia_int(
            "Vagas de garagem: ",
            valido=lambda v: v >= 0,
            erro="Não pode ser negativo."
        )
        imovel = Casa(quartos=quartos, vagas=vagas)

    else:
        vagas = leia_int(
            "Vagas de estacionamento: ",
            valido=lambda v: v >= 0,
            erro="Não pode ser negativo."
        )
        imovel = Estudio(vagas=vagas)

    parcelas = leia_int(
        f"Nº de parcelas do contrato [1..{MAX_INSTALLMENTS}]: ",
        valido=lambda p: 1 <= p <= MAX_INSTALLMENTS,
        erro=f"Parcelas devem estar entre 1 e {MAX_INSTALLMENTS}."
    )

    orc = Orcamento(imovel=imovel, parcelas_contrato=parcelas)
    orc.validar()

    # ===== salva na Área de Trabalho =====
    desktop_dir = get_desktop_path()
    desktop_dir.mkdir(parents=True, exist_ok=True)

    nome_arquivo = input("Nome do arquivo CSV (ENTER = parcelas_orcamento.csv): ")
    nome_arquivo = ensure_csv_suffix(nome_arquivo or "parcelas_orcamento.csv")

    filepath = desktop_dir / nome_arquivo

    linhas = orc.gerar_parcelas()

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            campos = ["mes", "aluguel", "parcela_contrato", "total"]
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(linhas)

        print_resumo(orc, linhas)
        print(f"\n✅ Arquivo CSV salvo em: {filepath}")
        print("Geração concluída com sucesso!")
    except OSError as e:
        print(f"\n❌ Erro ao salvar o arquivo: {e}")

if __name__ == "__main__":
    main()