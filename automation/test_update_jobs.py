import unittest
from datetime import datetime
from unittest.mock import patch
from types import SimpleNamespace

from automation import update_jobs as jobs


class CollectionTests(unittest.TestCase):
    def test_deadlines(self):
        for text, expected in [
            ('접수기간 2026.09.01 ~ 2026.09.15 17:00', '2026-09-15T17:00:00+09:00'),
            ('접수기간 2026.09.01 ~ 09.15(화) 17:00', '2026-09-15T17:00:00+09:00'),
            ('마감일 26.09.13(일) 23:00', '2026-09-13T23:00:00+09:00'),
            ('마감일 2026년 9월 15일 17시', '2026-09-15T17:00:00+09:00'),
            ('접수기간 2024.01.01 ~ 2024.01.15 10:00', '2024-01-15T10:00:00+09:00'),
        ]:
            with self.subTest(text=text):
                self.assertEqual(jobs.deadline_from(text).isoformat(), expected)

    def test_api_evidence_wins_over_navigation(self):
        company = {'name': '카카오', 'career_home': 'https://careers.kakao.com'}
        api = {'url':'https://careers.kakao.com/jobs/123', 'title':'데이터 엔지니어 인턴', 'snippet':'SQL Python', 'discoveredBy':'official_api'}
        nav = {**api, 'snippet':'채용 공고', 'discoveredBy':'official_page'}
        with patch.object(jobs,'kakao_api_results',return_value=[api]), patch.object(jobs,'direct_results',return_value=[nav]), patch.object(jobs,'sitemap_results',return_value=[]), patch.object(jobs,'bing_results',return_value=[]):
            result, errors=jobs.discover(company)
        self.assertEqual(result,[api])
        self.assertEqual(errors,[])

    def test_expired_job_removed_even_when_source_unavailable(self):
        with patch.object(jobs,'fetch_page',side_effect=AssertionError('must not fetch')):
            self.assertIsNone(jobs.revalidate_existing({'deadline':'2020-01-01T17:00:00+09:00'},[],''))

    def test_public_it_and_ai_are_relevant(self):
        for title in ['전산 신입 채용', '정보기술 신입 채용', 'AI 신입 채용', 'IT 개발운영 신입 채용']:
            self.assertTrue(jobs.technical_relevance(title,''))
        self.assertFalse(jobs.technical_relevance('시설관리 신입 채용',''))

    def test_expired_posting_rejected(self):
        candidate={'company':'테스트','title':'데이터 엔지니어 신입 채용','url':'https://example.com/jobs/1','snippet':'신입 SQL Python','discoveredBy':'official_api'}
        result,reason=jobs.classify(candidate,'접수기간 2020.01.01 ~ 2020.01.15 17:00')
        self.assertIsNone(result)
        self.assertEqual(reason,'expired')

    def test_only_http_official_links(self):
        self.assertFalse(jobs.official('javascript:alert(1)',['example.com']))
        self.assertFalse(jobs.official('https://example.com.evil.test/job',['example.com']))
        self.assertTrue(jobs.official('https://jobs.example.com/job',['example.com']))

    def test_scholarship_is_not_entry_level_employment(self):
        candidate={'company':'테스트','title':'SW 개발','url':'https://example.com/jobs/1','snippet':'신입','discoveredBy':'official_api'}
        result,reason=jobs.classify(candidate,'[장학생] 특정 대학 3-4학년 대상 선발. 신입 채용은 다른 공고를 확인하세요.')
        self.assertIsNone(result)
        self.assertEqual(reason,'scholarship_only')

    def test_euc_kr_page_evidence_is_readable(self):
        content = ('<meta charset="euc-kr"><main>' + '전산 신입 채용 정보기술 ' * 30 + '</main>').encode('euc-kr')
        response = SimpleNamespace(content=content, headers={'content-type':'text/html'}, raise_for_status=lambda:None)
        jobs.fetch_page.cache_clear()
        with patch.object(jobs.requests,'get',return_value=response):
            text,error=jobs.fetch_page('https://example.com/encoding-test')
        self.assertIsNone(error)
        self.assertIn('전산 신입 채용',text)
        jobs.fetch_page.cache_clear()


if __name__ == '__main__':
    unittest.main()
