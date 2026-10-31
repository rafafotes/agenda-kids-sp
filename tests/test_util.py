import unittest
from datetime import date

from crawler import util
from crawler.adaptadores import _linhas_repetidas

REF = date(2026, 10, 31)


class TestDatas(unittest.TestCase):
    def test_formatos_basicos(self):
        self.assertEqual(util.datas_no_texto("Dia 08/11 às 15h", REF), [date(2026, 11, 8)])
        self.assertEqual(util.datas_no_texto("em 6 de novembro de 2026", REF), [date(2026, 11, 6)])
        self.assertEqual(util.datas_no_texto("Sábado, 7 de Dezembro", REF), [date(2026, 12, 7)])

    def test_virada_do_ano(self):
        # janeiro sem ano, visto em outubro, é do ano seguinte
        self.assertEqual(util.datas_no_texto("férias: 15/01", REF), [date(2027, 1, 15)])

    def test_intervalo_no_mesmo_mes(self):
        self.assertEqual(util.periodo_do_texto("de 27 a 30 de novembro", REF), (date(2026, 11, 27), date(2026, 11, 30)))

    def test_ate(self):
        self.assertEqual(util.periodo_do_texto("Até 09/11, a cada R$ 500", REF), (None, date(2026, 11, 9)))

    def test_sem_data(self):
        self.assertEqual(util.periodo_do_texto("Venha se divertir!", REF), (None, None))


class TestClassificadores(unittest.TestCase):
    def test_infantil(self):
        self.assertGreaterEqual(util.pontuacao_infantil("Oficina de Cartinhas", "Para crianças de 3 a 10 anos"), 2)

    def test_promocao_nao_e_infantil(self):
        self.assertLess(util.pontuacao_infantil("Aniversário Premiado", "cadastre suas notas fiscais e concorra no sorteio"), 2)

    def test_pet_e_retrospectiva(self):
        self.assertLess(util.pontuacao_infantil("Caça aos Biscoitos", "convida pets e seus tutores, traga seu pet fantasiado"), 2)
        self.assertLess(util.pontuacao_infantil("Voltinha", "A Voltinha foi repleta de momentos especiais com as crianças"), 4)

    def test_rodape_nao_penaliza(self):
        texto = "Oficina de pintura para crianças. Horário de funcionamento: domingos e feriados 14h"
        self.assertGreaterEqual(util.pontuacao_infantil("Vamos fazer arte", texto), 2)

    def test_agendamento_e_gratuidade(self):
        self.assertTrue(util.precisa_agendar("Inscrições pelo app do shopping"))
        self.assertTrue(util.gratuito("Atividade gratuita"))
        self.assertFalse(util.gratuito("Ingressos a partir de R$ 40"))
        self.assertIsNone(util.gratuito("Venha!"))

    def test_faixa_etaria_e_natal(self):
        self.assertEqual(util.faixa_etaria("para crianças de 3 a 12 anos"), "3 a 12 anos")
        self.assertEqual(util.faixa_etaria("a partir de 4 anos"), "a partir de 4 anos")
        self.assertTrue(util.eh_natal("Chegada do Papai Noel"))

    def test_horario(self):
        self.assertEqual(util.horario("Segunda a sábado: 14h às 21h | Domingos: 12h às 19h"), "das 14h às 21h")
        self.assertEqual(util.horario("Paradas às 14h, 16h e 18h"), "14h, 16h, 18h")


class TestLimpeza(unittest.TestCase):
    def test_titulo(self):
        self.assertEqual(util.limpar_titulo("Rainbow Beez | Tietê Plaza", "Tietê Plaza Shopping"), "Rainbow Beez")
        self.assertEqual(util.limpar_titulo("Hora do Conto  no Iguatemi: Sua Próxima Experiência", "Shopping Pátio Paulista"), "Hora do Conto")
        self.assertEqual(util.limpar_titulo("Noel Kids Run - 2° Edição", "Golden Square Shopping"), "Noel Kids Run - 2° Edição")

    def test_boilerplate(self):
        corpos = ["Menu\nEvento A\nRodapé", "Menu\nEvento B\nRodapé", "Menu\nEvento C\nRodapé"]
        self.assertEqual(_linhas_repetidas(corpos), {"Menu", "Rodapé"})


if __name__ == "__main__":
    unittest.main()
