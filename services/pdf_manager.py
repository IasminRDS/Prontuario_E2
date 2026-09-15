import pikepdf
from pypdf import PdfReader, PdfWriter
import os

class PDFManager:
    @staticmethod
    def compactar_pdf(caminho_entrada, caminho_saida, nivel='medio'):
        """ Comprime o PDF. Níveis: 'baixo', 'medio', 'alto' """
        try:
            with pikepdf.open(caminho_entrada) as pdf:
                save_args = {
                    "compress_streams": True,
                    "linearize": True # Prepara para visualização rápida na web
                }
                
                if nivel == 'alto':
                    save_args["image_mode"] = pikepdf.PdfImageMode.downsample
                    save_args["image_resolution"] = 72 # Máxima redução de tamanho
                elif nivel == 'medio':
                    save_args["image_mode"] = pikepdf.PdfImageMode.downsample
                    save_args["image_resolution"] = 150
                    
                pdf.save(caminho_saida, **save_args)
            return True
        except Exception as e:
            print(f"Erro na compactação: {e}")
            return False

    @staticmethod
    def proteger_pdf(caminho_entrada, caminho_saida, senha, permitir_impressao=False):
        """ Adiciona senha e restrições ao PDF. """
        try:
            reader = PdfReader(caminho_entrada)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            # Permissões: 0 = bloqueia tudo, 0b0000100 = permite impressão
            permissions_flag = 0b0000100 if permitir_impressao else 0
            
            # Criptografia AES
            writer.encrypt(user_password=senha, owner_password=senha, permissions_flag=permissions_flag)

            with open(caminho_saida, "wb") as f:
                writer.write(f)
            return True
        except Exception as e:
            print(f"Erro ao proteger PDF: {e}")
            return False

    @staticmethod
    def reorganizar_pdf(caminho_entrada, caminho_saida, nova_ordem):
        """
        Cria um novo PDF apenas com as páginas escolhidas e na ordem certa.
        nova_ordem: lista de inteiros com os índices das páginas (Ex: [0, 2, 1])
        """
        try:
            reader = PdfReader(caminho_entrada)
            writer = PdfWriter()

            for indice in nova_ordem:
                if 0 <= indice < len(reader.pages):
                    writer.add_page(reader.pages[indice])

            with open(caminho_saida, "wb") as f:
                writer.write(f)
            return True
        except Exception as e:
            print(f"Erro ao reorganizar PDF: {e}")
            return False