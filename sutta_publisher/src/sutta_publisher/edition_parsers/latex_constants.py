from pylatex.base_classes import UnsafeCommand

MATTERS_TO_SKIP: list[str] = [
    "endnotes",
]
STYLING_CLASSES: list[str] = [
    "namo",
    "endsection",
    "endsutta",
    "endbook",
    "endkanda",
    "end",
    "uddana-intro",
    "endvagga",
    "rule",
    "add",
    "evam",
    "speaker",
]
NEW_COMMANDS: dict[str, UnsafeCommand] = {
    # titlepage
    "titlepageTranslationTitle": UnsafeCommand(
        "newcommand*",
        arguments="\\titlepageTranslationTitle",
        options=1,
        extra_arguments="{\\begin{center}\\begin{large}{#1}\\end{large}\\end{center}}",
    ),
    "titlepageCreatorName": UnsafeCommand(
        "newcommand*",
        arguments="\\titlepageCreatorName",
        options=1,
        extra_arguments="{\\begin{center}\\begin{normalsize}{#1}\\end{normalsize}\\end{center}}",
    ),
    # halftitlepage
    "halftitlepageTranslationTitle": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageTranslationTitle",
        options=1,
        extra_arguments="\\setstretch{2.5}{\\begin{center}\\begin{Huge}\\uppercase{\\so{#1}}\\end{Huge}\\end{center}}",
    ),
    "halftitlepageTranslationSubtitle": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageTranslationSubtitle",
        options=1,
        extra_arguments="\\setstretch{1.2}{\\begin{center}\\begin{large}{#1}\\end{large}\\end{center}}",
    ),
    # TODO: Uncomment when ready to use Arno
    # "halftitlepageFleuron": UnsafeCommand(
    #     "newcommand*",
    #     arguments="\\halftitlepageFleuron",
    #     options=1,
    #     extra_arguments="{\\begin{center}\\begin{large}\\ArnoProornmZero{{#1}}\\end{large}\\end{center}}"
    # ),
    "halftitlepageByline": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageByline",
        options=1,
        extra_arguments="{\\begin{center}\\begin{normalsize}\\textit{{#1}}\\end{normalsize}\\end{center}}",
    ),
    "halftitlepageCreatorName": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageCreatorName",
        options=1,
        extra_arguments="{\\begin{center}\\begin{LARGE}{\\caps{#1}}\\end{LARGE}\\end{center}}",
    ),
    "halftitlepageVolumeNumber": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageVolumeNumber",
        options=1,
        extra_arguments="{\\begin{center}\\begin{normalsize}{#1}\\end{normalsize}\\end{center}}",
    ),
    "halftitlepageVolumeAcronym": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageVolumeAcronym",
        options=1,
        extra_arguments="{\\begin{center}\\begin{normalsize}{#1}\\end{normalsize}\\end{center}}",
    ),
    "halftitlepageVolumeTranslationTitle": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageVolumeTranslationTitle",
        options=1,
        extra_arguments="{\\begin{center}\\begin{normalsize}{#1}\\end{normalsize}\\end{center}}",
    ),
    "halftitlepageVolumeRootTitle": UnsafeCommand(
        "newcommand*",
        arguments="\\halftitlepageVolumeRootTitle",
        options=1,
        extra_arguments="{\\begin{center}\\begin{normalsize}{#1}\\end{normalsize}\\end{center}}",
    ),
    # TODO: Uncomment when ready to use Arno
    # "halftitlepagePublisher": UnsafeCommand(
    #     "newcommand*",
    #     arguments="\\halftitlepagePublisher",
    #     options=1,
    #     extra_arguments="{\\begin{center}\\begin{LARGE}{\\ArnoProNoLigatures\\caps{#1}}\\end{LARGE}\\end{center}}"
    # ),
    # mainmatter
    "scnamo": UnsafeCommand(
        "newcommand*",
        arguments="\\scnamo",
        options=1,
        extra_arguments="\\begin{center}\\textit{#1}\\end{center}",
    ),
    "scendsection": UnsafeCommand(
        "newcommand",
        arguments="\\scendsection",
        options=1,
        extra_arguments="\\begin{center}\\textit{#1}\\end{center}",
    ),
    "scendsutta": UnsafeCommand(
        "newcommand",
        arguments="\\scendsutta",
        options=1,
        extra_arguments="\\begin{center}\\textit{#1}\\end{center}",
    ),
    "scendbook": UnsafeCommand(
        "newcommand",
        arguments="\\scendbook",
        options=1,
        extra_arguments="\\begin{center}\\uppercase{#1}\\end{center}",
    ),
    "scendkanda": UnsafeCommand(
        "newcommand",
        arguments="\\scendkanda",
        options=1,
        extra_arguments="\\begin{center}\\textbf{#1}\\end{center}",
    ),
    "scend": UnsafeCommand(
        "newcommand",
        arguments="\\scend",
        options=1,
        extra_arguments="\\begin{center}\\textit{#1}\\end{center}",
    ),
    "scuddanaintro": UnsafeCommand(
        "newcommand",
        arguments="\\scuddanaintro",
        options=1,
        extra_arguments="\\textit{#1}",
    ),
    "scendvagga": UnsafeCommand(
        "newcommand",
        arguments="\\scendvagga",
        options=1,
        extra_arguments="\\begin{center}\\textbf{#1}\\end{center}",
    ),
    "scrule": UnsafeCommand(
        "newcommand",
        arguments="\\scrule",
        options=1,
        extra_arguments="\\textbf{#1}",
    ),
    "scadd": UnsafeCommand(
        "newcommand",
        arguments="\\scadd",
        options=1,
        extra_arguments="\\textit{#1}",
    ),
    "scevam": UnsafeCommand(
        "newcommand*",
        arguments="\\scevam",
        options=1,
        extra_arguments="\\caps{#1}",
    ),
    "scspeaker": UnsafeCommand(
        "newcommand*",
        arguments="\\scspeaker",
        options=1,
        extra_arguments="\\hspace{2em}\\textit{#1}",
    ),
}
