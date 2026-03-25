import pytest
from unittest.mock import MagicMock, patch
from analysis_tool import MatchAnalysis, PersonalBetAnalysisTool


@pytest.fixture
def tool():
    return PersonalBetAnalysisTool()


@pytest.fixture
def sample_data():
    return {
        "home": {
            "name": "Benfica",
            "recent_results": ["W", "W", "D", "W", "L"],
            "goals_scored_avg": 2.0,
            "shots_on_target_avg": 5.4,
            "goals_conceded_avg": 0.8,
            "clean_sheet_rate": 0.4,
        },
        "away": {
            "name": "Braga",
            "recent_results": ["W", "L", "D", "W", "D"],
            "goals_scored_avg": 1.4,
            "shots_on_target_avg": 4.2,
            "goals_conceded_avg": 1.2,
            "clean_sheet_rate": 0.2,
        },
    }


class TestCalculateFormScore:
    def test_all_wins(self, tool):
        assert tool.calculate_form_score(["W", "W", "W"]) == 3.0

    def test_all_losses(self, tool):
        assert tool.calculate_form_score(["L", "L", "L"]) == 0.0

    def test_all_draws(self, tool):
        assert tool.calculate_form_score(["D", "D", "D"]) == 1.0

    def test_mixed_results(self, tool):
        # W=3, D=1, L=0 -> total=4, avg=4/3 ≈ 1.33
        assert tool.calculate_form_score(["W", "D", "L"]) == round(4 / 3, 2)

    def test_empty_results(self, tool):
        assert tool.calculate_form_score([]) == 0.0

    def test_sample_home_results(self, tool):
        # W W D W L -> 3+3+1+3+0=10, avg=2.0
        assert tool.calculate_form_score(["W", "W", "D", "W", "L"]) == 2.0

    def test_sample_away_results(self, tool):
        # W L D W D -> 3+0+1+3+1=8, avg=1.6
        assert tool.calculate_form_score(["W", "L", "D", "W", "D"]) == 1.6


class TestCalculateAttackScore:
    def test_basic(self, tool):
        result = tool.calculate_attack_score(2.0, 5.0)
        assert result == round(2.0 * 0.6 + 5.0 * 0.4, 2)

    def test_zeros(self, tool):
        assert tool.calculate_attack_score(0.0, 0.0) == 0.0


class TestCalculateDefenseScore:
    def test_perfect_defense(self, tool):
        # 0 goals conceded, 100% clean sheets
        result = tool.calculate_defense_score(0.0, 1.0)
        expected = round(((1.0 * 0.6) + ((3 - 0) / 3 * 0.4)) * 10, 2)
        assert result == expected

    def test_poor_defense(self, tool):
        # 3+ goals conceded, no clean sheets
        result = tool.calculate_defense_score(3.0, 0.0)
        assert result == 0.0

    def test_goals_conceded_capped_at_zero(self, tool):
        # goals_conceded_avg > 3 should not produce negative values
        result = tool.calculate_defense_score(5.0, 0.0)
        assert result >= 0.0


class TestAnalyzeMatch:
    def test_returns_match_analysis(self, tool, sample_data):
        analysis = tool.analyze_match(sample_data)
        assert isinstance(analysis, MatchAnalysis)

    def test_team_names(self, tool, sample_data):
        analysis = tool.analyze_match(sample_data)
        assert analysis.home_team == "Benfica"
        assert analysis.away_team == "Braga"

    def test_home_win_recommendation(self, tool):
        data = {
            "home": {
                "name": "StrongHome",
                "recent_results": ["W", "W", "W", "W", "W"],
                "goals_scored_avg": 3.0,
                "shots_on_target_avg": 8.0,
                "goals_conceded_avg": 0.2,
                "clean_sheet_rate": 0.9,
            },
            "away": {
                "name": "WeakAway",
                "recent_results": ["L", "L", "L", "L", "L"],
                "goals_scored_avg": 0.2,
                "shots_on_target_avg": 1.0,
                "goals_conceded_avg": 3.0,
                "clean_sheet_rate": 0.0,
            },
        }
        analysis = tool.analyze_match(data)
        assert analysis.recommendation == "Lean: Home Win"
        assert analysis.confidence > 50.0

    def test_away_win_recommendation(self, tool):
        data = {
            "home": {
                "name": "WeakHome",
                "recent_results": ["L", "L", "L", "L", "L"],
                "goals_scored_avg": 0.2,
                "shots_on_target_avg": 1.0,
                "goals_conceded_avg": 3.0,
                "clean_sheet_rate": 0.0,
            },
            "away": {
                "name": "StrongAway",
                "recent_results": ["W", "W", "W", "W", "W"],
                "goals_scored_avg": 3.0,
                "shots_on_target_avg": 8.0,
                "goals_conceded_avg": 0.2,
                "clean_sheet_rate": 0.9,
            },
        }
        analysis = tool.analyze_match(data)
        assert analysis.recommendation == "Lean: Away Win"
        assert analysis.confidence > 50.0

    def test_balanced_recommendation(self, tool):
        data = {
            "home": {
                "name": "TeamA",
                "recent_results": ["W", "D", "L"],
                "goals_scored_avg": 1.0,
                "shots_on_target_avg": 3.0,
                "goals_conceded_avg": 1.0,
                "clean_sheet_rate": 0.3,
            },
            "away": {
                "name": "TeamB",
                "recent_results": ["W", "D", "L"],
                "goals_scored_avg": 1.0,
                "shots_on_target_avg": 3.0,
                "goals_conceded_avg": 1.0,
                "clean_sheet_rate": 0.3,
            },
        }
        analysis = tool.analyze_match(data)
        assert analysis.recommendation == "Lean: Balanced / No strong edge"
        assert analysis.confidence == 50.0

    def test_confidence_capped_at_90(self, tool):
        data = {
            "home": {
                "name": "Elite",
                "recent_results": ["W"] * 10,
                "goals_scored_avg": 5.0,
                "shots_on_target_avg": 10.0,
                "goals_conceded_avg": 0.0,
                "clean_sheet_rate": 1.0,
            },
            "away": {
                "name": "Bottom",
                "recent_results": ["L"] * 10,
                "goals_scored_avg": 0.0,
                "shots_on_target_avg": 0.0,
                "goals_conceded_avg": 5.0,
                "clean_sheet_rate": 0.0,
            },
        }
        analysis = tool.analyze_match(data)
        assert analysis.confidence <= 90.0

    def test_missing_optional_fields_use_defaults(self, tool):
        data = {
            "home": {},
            "away": {},
        }
        analysis = tool.analyze_match(data)
        assert analysis.home_team == "Home"
        assert analysis.away_team == "Away"
        assert analysis.home_form_score == 0.0
        assert analysis.away_form_score == 0.0


class TestGetMatchData:
    def test_successful_request(self, tool):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "123", "home": {}, "away": {}}
        mock_response.raise_for_status.return_value = None

        with patch.object(tool.session, "get", return_value=mock_response):
            result = tool.get_match_data("123")

        assert result == {"id": "123", "home": {}, "away": {}}

    def test_request_exception_returns_none(self, tool):
        import requests as req

        with patch.object(tool.session, "get", side_effect=req.RequestException("timeout")):
            result = tool.get_match_data("999")

        assert result is None


class TestPrintAnalysis:
    def test_print_output(self, tool, sample_data, capsys):
        analysis = tool.analyze_match(sample_data)
        tool.print_analysis(analysis)
        captured = capsys.readouterr()
        assert "Benfica" in captured.out
        assert "Braga" in captured.out
        assert "Recommendation:" in captured.out
        assert "Confidence:" in captured.out
