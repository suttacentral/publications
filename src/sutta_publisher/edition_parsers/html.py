from sutta_publisher.shared.value_objects.edition import EditionType

from .base import EditionParser, log
from .helper_functions import _process_a_line


class HtmlEdition(EditionParser):
    edition_type = EditionType.html

    def __generate_html(self) -> str:
        """Generate content of an HTML body"""
        log.info("Generating html...")
        html_output: list[str] = []
        for volume in self.raw_data:  # iterate over volumes
            volume_html: list[str] = []
            for volume_content in volume.mainmatter:  # iterate over matters in each volume
                volume_text: dict[str, str] = volume_content.mainmatter.main_text
                markup: dict[str, str] = volume_content.mainmatter.markup
                reference: dict[str, str] = volume_content.mainmatter.reference
                for segment_id, text in volume_text.items():
                    references_per_segment_id = reference[segment_id].split(", ")
                    volume_html.append(
                        _process_a_line(
                            markup=markup[segment_id],
                            segment_id=segment_id,
                            text=text,
                            references=references_per_segment_id,
                            possible_refs=self.possible_refs,
                        )
                    )
            html_output.append("".join(volume_html))
        return "".join(html_output)
