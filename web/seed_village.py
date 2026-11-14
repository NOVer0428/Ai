"""기본 제공 15종 템플릿 묶음.

설계: Codex 설계안(매스·재료 역할) + 핀터레스트 이미지 관찰(design/references-2026.md) → Claude 구현.
모든 블록은 seed_kit/template_format.state() 로 26.3 블록 데이터에서 만든다.
"""
from village_craft import craft_templates
from village_east import east_templates
from village_world import world_templates


def village_templates():
    return east_templates() + craft_templates() + world_templates()
