from __future__ import annotations

import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import build_dashboard as dashboard


class DashboardBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        temporary_root = Path(cls.temp_dir.name)
        cls.first_output = temporary_root / "first.html"
        cls.second_output = temporary_root / "second.html"

        cls.data = dashboard.build_dashboard(
            dashboard.DEFAULT_CUTOFF_DATE, cls.first_output
        )
        dashboard.build_dashboard(
            dashboard.DEFAULT_CUTOFF_DATE, cls.second_output
        )
        cls.html = cls.first_output.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_results_from_questions_match_validated_notebooks(self) -> None:
        top_ids = self.data["q4"]["top10"]["customer_id"].astype(int).tolist()
        self.assertEqual(top_ids, dashboard.EXPECTED_TOP10_CUSTOMERS)
        self.assertEqual(self.data["q4"]["category"], "Hélices")
        self.assertEqual(self.data["q4"]["category_quantity"], 492)

        self.assertEqual(self.data["q5"]["worst_day"], "Quinta-feira")
        self.assertEqual(self.data["q5"]["worst_average"], 151_027.72)
        self.assertEqual(self.data["q5"]["calendar_days"], 2_418)
        self.assertEqual(self.data["q5"]["zero_sales_days"], 76)

        self.assertEqual(self.data["q6"]["forecast_total"], 149)
        self.assertEqual(self.data["q6"]["actual_total"], 207)
        self.assertEqual(round(self.data["q6"]["mae"], 2), 19.44)

        recommendation = self.data["q7"]["ranking"].iloc[0]
        self.assertEqual(recommendation["name"], "Motor de Popa 5331")
        self.assertEqual(round(float(recommendation["similaridade"]), 6), 0.256553)

    def test_executive_metrics_match_audited_snapshot(self) -> None:
        self.assertEqual(self.data["channels"]["business_orders"], 38_097)
        self.assertEqual(
            round(self.data["channels"]["total_revenue"], 2),
            1_096_687_344.91,
        )
        self.assertEqual(self.data["returns"]["completed_returns"], 717)
        self.assertEqual(
            round(self.data["returns"]["refund_total"], 2), 4_276_548.78
        )
        expected_returns = {
            "Cliente desistiu da compra": (130, 873_594.16),
            "Compra duplicada": (123, 784_111.58),
            "Produto avariado no transporte": (114, 678_958.86),
            "Tamanho/cor incorretos": (109, 645_750.81),
            "Produto com defeito de fábrica": (106, 564_727.03),
            "Item não corresponde à descrição": (117, 529_486.44),
            "Não informado": (10, 134_207.51),
            "Outros": (8, 65_712.39),
        }
        actual_returns = {
            row.motivo: (int(row.devolucoes), round(float(row.reembolso), 2))
            for row in self.data["returns"]["ranking"].itertuples()
        }
        self.assertEqual(actual_returns, expected_returns)

        self.assertEqual(self.data["suppliers"]["completed_orders"], 879)
        self.assertEqual(self.data["suppliers"]["late_orders"], 160)
        self.assertEqual(
            round(self.data["suppliers"]["overall_on_time"] * 100, 2), 81.80
        )
        self.assertEqual(
            self.data["suppliers"]["ranking"]["supplier_id"].head(5).tolist(),
            [22, 4, 10, 15, 19],
        )
        self.assertEqual(
            round(self.data["suppliers"]["average_late_days"], 2), 10.24
        )

    def test_build_is_deterministic_for_fixed_cutoff(self) -> None:
        first_hash = hashlib.sha256(self.first_output.read_bytes()).hexdigest()
        second_hash = hashlib.sha256(self.second_output.read_bytes()).hexdigest()
        self.assertEqual(first_hash, second_hash)

    def test_html_is_static_responsive_and_self_contained(self) -> None:
        self.assertIn('<html lang="pt-BR">', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertIn("Plotly.newPlot", self.html)
        self.assertNotRegex(self.html, r"<script[^>]+src=")
        self.assertNotRegex(self.html, r"<link[^>]+href=[\"']https?://")
        self.assertNotIn("C:\\", self.html)

        plot_ids = re.findall(r'<div id="(plot-[^"]+)"', self.html)
        self.assertEqual(
            set(plot_ids),
            {
                "plot-channels",
                "plot-customers",
                "plot-weekday",
                "plot-forecast",
                "plot-returns",
                "plot-suppliers",
                "plot-recommendations",
            },
        )

    def test_published_directory_contains_only_static_assets(self) -> None:
        published_files = [
            path
            for path in (PROJECT_ROOT / "dashboard").rglob("*")
            if path.is_file()
        ]
        forbidden_suffixes = {".csv", ".json", ".env"}
        self.assertFalse(
            [path for path in published_files if path.suffix in forbidden_suffixes]
        )
        self.assertTrue((PROJECT_ROOT / "dashboard" / "assets" / "styles.css").is_file())
        self.assertTrue((PROJECT_ROOT / "dashboard" / "assets" / "favicon.svg").is_file())

    def test_new_dashboard_files_do_not_use_em_dash(self) -> None:
        files = [
            PROJECT_ROOT / "src" / "build_dashboard.py",
            PROJECT_ROOT / "dashboard" / "README.md",
            PROJECT_ROOT / "dashboard" / "assets" / "styles.css",
            PROJECT_ROOT / "dashboard" / "assets" / "favicon.svg",
            PROJECT_ROOT / ".github" / "workflows" / "pages.yml",
        ]
        for path in files:
            with self.subTest(path=path):
                self.assertNotIn("\u2014", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
