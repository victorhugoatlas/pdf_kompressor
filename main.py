import io
import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
import pymupdf as fitz
from PIL import Image

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DPI_ALVO = 120
QUALIDADE_JPEG = 45


def comprimir_pdf_otimizado(caminho_entrada, caminho_saida):
    doc = fitz.open(caminho_entrada)

    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]

            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                img = Image.open(io.BytesIO(image_bytes))
                largura_orig, altura_orig = img.size

                fator_escala = DPI_ALVO / 72.0
                nova_largura = int(largura_orig / fator_escala)
                nova_altura = int(altura_orig / fator_escala)

                if largura_orig > nova_largura and nova_largura > 0:
                    img = img.resize(
                        (nova_largura, nova_altura), Image.Resampling.LANCZOS
                    )

                if img.mode in ("RGBA", "P", "CMYK"):
                    img = img.convert("RGB")

                buffer = io.BytesIO()
                img.save(
                    buffer, format="JPEG", quality=QUALIDADE_JPEG, optimize=True
                )

                page.replace_image(xref, stream=buffer.getvalue())

            except Exception:
                continue

    doc.save(caminho_saida, garbage=4, deflate=True, clean=True)
    doc.close()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PDF Kompressor by VH")
        self.geometry("520x420")
        self.resizable(False, False)

        self.label_titulo = ctk.CTkLabel(
            self, text="Compressor de PDF", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.label_titulo.pack(pady=(20, 15))

        self.frame_origem = ctk.CTkFrame(self)
        self.frame_origem.pack(fill="x", padx=20, pady=5)

        self.entry_origem = ctk.CTkEntry(
            self.frame_origem, placeholder_text="Pasta de Origem..."
        )
        self.entry_origem.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)

        self.btn_origem = ctk.CTkButton(
            self.frame_origem, text="Buscar", width=80, command=self.selecionar_origem
        )
        self.btn_origem.pack(side="right", padx=(5, 10), pady=10)

        self.frame_destino = ctk.CTkFrame(self)
        self.frame_destino.pack(fill="x", padx=20, pady=5)

        self.entry_destino = ctk.CTkEntry(
            self.frame_destino, placeholder_text="Pasta de Destino..."
        )
        self.entry_destino.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)

        self.btn_destino = ctk.CTkButton(
            self.frame_destino, text="Buscar", width=80, command=self.selecionar_destino
        )
        self.btn_destino.pack(side="right", padx=(5, 10), pady=10)

        self.btn_iniciar = ctk.CTkButton(
            self,
            text="Iniciar Compressão",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f538d",
            hover_color="#14375e",
            height=40,
            command=self.iniciar_processamento_thread,
        )
        self.btn_iniciar.pack(fill="x", padx=20, pady=15)

        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=20, pady=(0, 10))
        self.progress.set(0)

        # Corrigido: parâmetro activate_scroll removido
        self.textbox_log = ctk.CTkTextbox(self, height=120)
        self.textbox_log.pack(fill="both", padx=20, pady=(0, 20))
        self.textbox_log.configure(state="disabled")

    def selecionar_origem(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.entry_origem.delete(0, "end")
            self.entry_origem.insert(0, pasta)
            if not self.entry_destino.get():
                self.entry_destino.insert(0, pasta + " compress")

    def selecionar_destino(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.entry_destino.delete(0, "end")
            self.entry_destino.insert(0, pasta)

    def log(self, mensagem):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", mensagem + "\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def iniciar_processamento_thread(self):
        pasta_in = self.entry_origem.get().strip()
        pasta_out = self.entry_destino.get().strip()

        if not pasta_in or not os.path.exists(pasta_in):
            messagebox.showerror("Erro", "Selecione uma pasta de origem válida!")
            return

        if not pasta_out:
            messagebox.showerror("Erro", "Selecione uma pasta de destino válida!")
            return

        self.btn_iniciar.configure(state="disabled")
        self.btn_origem.configure(state="disabled")
        self.btn_destino.configure(state="disabled")

        threading.Thread(
            target=self.processar_pasta, args=(pasta_in, pasta_out), daemon=True
        ).start()

    def processar_pasta(self, pasta_in, pasta_out):
        if not os.path.exists(pasta_out):
            os.makedirs(pasta_out)

        arquivos = [f for f in os.listdir(pasta_in) if f.lower().endswith(".pdf")]
        total = len(arquivos)

        if total == 0:
            self.log("Nenhum arquivo PDF encontrado na pasta.")
            self.finalizar()
            return

        self.log(f"Iniciando: {total} PDFs encontrados.")

        for i, arquivo in enumerate(arquivos, start=1):
            origem = os.path.join(pasta_in, arquivo)
            destino = os.path.join(pasta_out, arquivo)

            try:
                comprimir_pdf_otimizado(origem, destino)

                t_in = os.path.getsize(origem) / (1024 * 1024)
                t_out = os.path.getsize(destino) / (1024 * 1024)
                reducao = (1 - (t_out / t_in)) * 100 if t_in > 0 else 0

                self.log(
                    f"[{i}/{total}] {arquivo}: {t_in:.1f}MB ➔ {t_out:.1f}MB (-{reducao:.0f}%)"
                )
            except Exception as e:
                self.log(f"[{i}/{total}] Erro em {arquivo}: {e}")

            self.progress.set(i / total)

        self.log("Concluído com sucesso!")
        self.finalizar()

    def finalizar(self):
        self.btn_iniciar.configure(state="normal")
        self.btn_origem.configure(state="normal")
        self.btn_destino.configure(state="normal")


if __name__ == "__main__":
    app = App()
    app.mainloop()