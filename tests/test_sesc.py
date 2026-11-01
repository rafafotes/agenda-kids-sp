import unittest
from datetime import date

from crawler.adaptadores import _sesc_atividade

HOJE = date(2026, 11, 1)
FONTE = {}


def atividade(titulo, publico, primeira="2026-11-07T10:00", ultima="2026-11-07T10:00", **extra):
    base = {
        "id": 1, "titulo": titulo, "complemento": "", "link": "/programacao/x", "imagem": None,
        "publico_tag": [{"titulo": p} for p in publico], "categorias": [], "tipos_linguagens": [],
        "dataPrimeiraSessao": primeira, "dataUltimaSessao": ultima, "dataProxSessao": primeira,
        "gratuito": "Atividade gratuita", "cancelado": "", "esgotado": "",
        "qtdeIngressosWeb": None, "qtdeIngressosRede": None,
    }
    base.update(extra)
    return _sesc_atividade(base, "Pinheiros", "Pinheiros", "Zona Oeste", HOJE, FONTE)


class TestSesc(unittest.TestCase):
    def test_publico_criancas_entra(self):
        c = atividade("Circo Secreto", ["Crianças"])
        self.assertTrue(c["infantil_fonte"])
        self.assertEqual(c["local"], "Sesc Pinheiros")
        self.assertTrue(c["gratuito"])
        self.assertEqual(c["horario"], "próxima sessão 7/11 às 10h")

    def test_diversas_idades_precisa_de_sinal_infantil(self):
        self.assertIsNone(atividade("Customização de chinelos com macramê", ["Diversas idades"]))
        self.assertIsNotNone(atividade("Jogos e Brincadeiras Africanas", ["Diversas idades"]))

    def test_programa_continuo_e_cancelado_saem(self):
        self.assertIsNone(atividade("Curumim", ["Crianças"], primeira="2026-01-05T09:00", ultima="2026-12-18T09:00"))
        self.assertIsNone(atividade("Teatro", ["Crianças"], cancelado="Cancelado"))

    def test_venda_de_ingressos_e_esgotado(self):
        c = atividade("Espetáculo", ["Crianças"], gratuito="", qtdeIngressosWeb=0, esgotado="Esgotado")
        self.assertTrue(c["agendamento"])
        self.assertFalse(c["gratuito"])
        self.assertTrue(c["esgotado"])


if __name__ == "__main__":
    unittest.main()
