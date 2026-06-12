import json
from pathlib import Path

from app.config import get_settings
from app.llm import generate_artifacts
from app.models import ForgeSession


def main() -> None:
    items = json.loads((Path(__file__).parents[1] / "test_corpus/features.json").read_text())
    settings = get_settings()
    passed = 0
    for item in items:
        session = ForgeSession(
            feature_name=item["name"],
            feature_description=item["description"],
            domain_pack=item["domain"],
        )
        try:
            result = generate_artifacts(session, settings)
            assert result.artifacts.user_stories
            assert result.artifacts.api_contract.endpoints
            assert result.artifacts.state_machine.transitions
            print(f"PASS  {item['name']}  ({result.model}, {result.latency_ms} ms)")
            passed += 1
        except Exception as exc:
            print(f"FAIL  {item['name']}: {exc}")
    print(f"\n{passed}/{len(items)} corpus items passed schema validation.")
    raise SystemExit(0 if passed == len(items) else 1)


if __name__ == "__main__":
    main()
