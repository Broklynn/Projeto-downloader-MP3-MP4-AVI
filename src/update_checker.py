import json
import requests
import threading
from typing import Optional, Dict, Any
from .version import APP_VERSION


class UpdateChecker:
    """
    Verifica se há atualizações disponíveis no GitHub.
    """

    def __init__(self, repo_url: str = "https://raw.githubusercontent.com/Broklynn/Projeto-downloader-MP3-MP4-AVI/main/version.json"):
        self.repo_url = repo_url
        self.current_version = APP_VERSION

    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """
        Verifica se há uma versão mais recente disponível.

        Returns:
            Dict com informações da atualização se disponível, None se não há atualização.
            Formato: {
                "version": "1.0.1",
                "download_url": "https://...",
                "notes": "Descrição das mudanças"
            }
        """
        try:
            response = requests.get(self.repo_url, timeout=10)
            response.raise_for_status()

            remote_data = response.json()
            remote_version = remote_data.get("version", "")

            if self._is_newer_version(remote_version):
                return {
                    "version": remote_version,
                    "download_url": remote_data.get("download_url", ""),
                    "notes": remote_data.get("notes", "")
                }

        except requests.RequestException as e:
            print(f"Erro ao verificar atualizações: {e}")
        except json.JSONDecodeError as e:
            print(f"Erro ao processar dados de versão: {e}")
        except Exception as e:
            print(f"Erro inesperado na verificação de atualização: {e}")

        return None

    def _is_newer_version(self, remote_version: str) -> bool:
        """
        Compara versões no formato semântico (major.minor.patch).
        """
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            remote_parts = [int(x) for x in remote_version.split('.')]

            # Preenche com zeros se necessário
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(remote_parts) < 3:
                remote_parts.append(0)

            return remote_parts > current_parts

        except (ValueError, AttributeError):
            # Se não conseguir comparar, assume que não há atualização
            return False

    def check_async(self, callback):
        """
        Verifica atualizações em segundo plano e chama callback com resultado.
        """
        def worker():
            result = self.check_for_updates()
            callback(result)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()