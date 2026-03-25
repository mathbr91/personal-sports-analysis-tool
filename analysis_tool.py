import requests
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Scoring constants
FORM_WEIGHT_MULTIPLIER = 1.2
MAX_GOALS_CONCEDED_BASELINE = 3
BASE_CONFIDENCE = 55.0
CONFIDENCE_MULTIPLIER = 5.0
MAX_CONFIDENCE = 90.0
DIFFERENCE_THRESHOLD = 2


@dataclass
class MatchAnalysis:
    home_team: str
    away_team: str
    home_form_score: float
    away_form_score: float
    home_attack_score: float
    away_attack_score: float
    home_defense_score: float
    away_defense_score: float
    recommendation: str
    confidence: float


class PersonalBetAnalysisTool:
    """
    Ferramenta simples para análise pessoal de jogos.
    Estrutura pensada para integrar com um fornecedor oficial de dados/widget.
    """

    def __init__(self, base_url: str = "https://api.example.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PersonalSportsAnalysisTool/1.0"
        })

    def get_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Exemplo de método que consulta dados de um jogo.
        Substitua o endpoint por um endpoint oficial/autorizado quando tiver acesso.
        """
        url = f"{self.base_url}/matches/{match_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            print(f"Erro ao obter dados do jogo: {exc}")
            return None

    def calculate_form_score(self, recent_results: list) -> float:
        """
        Converte resultados recentes em score simples.
        W = 3, D = 1, L = 0
        """
        score_map = {"W": 3, "D": 1, "L": 0}

        if not recent_results:
            return 0.0

        total = sum(score_map.get(result, 0) for result in recent_results)
        return round(total / len(recent_results), 2)

    def calculate_attack_score(self, goals_scored_avg: float, shots_on_target_avg: float) -> float:
        """
        Computes an attack score using a weighted formula:
        60% weight on average goals scored, 40% weight on average shots on target.
        Returns a value on a continuous scale reflecting offensive output.
        """
        return round((goals_scored_avg * 0.6) + (shots_on_target_avg * 0.4), 2)

    def calculate_defense_score(self, goals_conceded_avg: float, clean_sheet_rate: float) -> float:
        """
        Computes a defense score using a weighted formula:
        60% weight on clean sheet rate, 40% weight on goals-conceded efficiency.
        Goals conceded efficiency normalises average goals conceded against a baseline
        of MAX_GOALS_CONCEDED_BASELINE (3), capped at zero to avoid negative values.
        The combined value is scaled by 10 to produce a comparable range to other scores.
        """
        goals_efficiency = (
            max(0, MAX_GOALS_CONCEDED_BASELINE - goals_conceded_avg)
            / MAX_GOALS_CONCEDED_BASELINE
        )
        defense_value = (clean_sheet_rate * 0.6) + (goals_efficiency * 0.4)
        return round(defense_value * 10, 2)

    def _calculate_confidence(self, difference: float) -> float:
        """Returns confidence percentage capped at MAX_CONFIDENCE based on score difference."""
        return min(MAX_CONFIDENCE, BASE_CONFIDENCE + abs(difference) * CONFIDENCE_MULTIPLIER)

    def analyze_match(self, raw_data: Dict[str, Any]) -> MatchAnalysis:
        home = raw_data["home"]
        away = raw_data["away"]

        home_form = self.calculate_form_score(home.get("recent_results", []))
        away_form = self.calculate_form_score(away.get("recent_results", []))

        home_attack = self.calculate_attack_score(
            home.get("goals_scored_avg", 0),
            home.get("shots_on_target_avg", 0)
        )
        away_attack = self.calculate_attack_score(
            away.get("goals_scored_avg", 0),
            away.get("shots_on_target_avg", 0)
        )

        home_defense = self.calculate_defense_score(
            home.get("goals_conceded_avg", 0),
            home.get("clean_sheet_rate", 0)
        )
        away_defense = self.calculate_defense_score(
            away.get("goals_conceded_avg", 0),
            away.get("clean_sheet_rate", 0)
        )

        home_total = (home_form * FORM_WEIGHT_MULTIPLIER) + home_attack + home_defense
        away_total = (away_form * FORM_WEIGHT_MULTIPLIER) + away_attack + away_defense

        difference = round(home_total - away_total, 2)

        if difference > DIFFERENCE_THRESHOLD:
            recommendation = "Lean: Home Win"
            confidence = self._calculate_confidence(difference)
        elif difference < -DIFFERENCE_THRESHOLD:
            recommendation = "Lean: Away Win"
            confidence = self._calculate_confidence(difference)
        else:
            recommendation = "Lean: Balanced / No strong edge"
            confidence = 50.0

        return MatchAnalysis(
            home_team=home.get("name", "Home"),
            away_team=away.get("name", "Away"),
            home_form_score=home_form,
            away_form_score=away_form,
            home_attack_score=home_attack,
            away_attack_score=away_attack,
            home_defense_score=home_defense,
            away_defense_score=away_defense,
            recommendation=recommendation,
            confidence=round(confidence, 2)
        )

    def print_analysis(self, analysis: MatchAnalysis) -> None:
        print("=" * 50)
        print(f"Match: {analysis.home_team} vs {analysis.away_team}")
        print("=" * 50)
        print(f"Home form score: {analysis.home_form_score}")
        print(f"Away form score: {analysis.away_form_score}")
        print(f"Home attack score: {analysis.home_attack_score}")
        print(f"Away attack score: {analysis.away_attack_score}")
        print(f"Home defense score: {analysis.home_defense_score}")
        print(f"Away defense score: {analysis.away_defense_score}")
        print("-" * 50)
        print(f"Recommendation: {analysis.recommendation}")
        print(f"Confidence: {analysis.confidence}%")
        print("=" * 50)


def main():
    """
    Exemplo local com dados mockados.
    """
    tool = PersonalBetAnalysisTool()

    sample_data = {
        "home": {
            "name": "Benfica",
            "recent_results": ["W", "W", "D", "W", "L"],
            "goals_scored_avg": 2.0,
            "shots_on_target_avg": 5.4,
            "goals_conceded_avg": 0.8,
            "clean_sheet_rate": 0.4
        },
        "away": {
            "name": "Braga",
            "recent_results": ["W", "L", "D", "W", "D"],
            "goals_scored_avg": 1.4,
            "shots_on_target_avg": 4.2,
            "goals_conceded_avg": 1.2,
            "clean_sheet_rate": 0.2
        }
    }

    analysis = tool.analyze_match(sample_data)
    tool.print_analysis(analysis)


if __name__ == "__main__":
    main()
