"""Lossless natural text spans for independently conditioned speech requests.

Offsets always address the original Python string. No normalization, inserted
punctuation, or stripping is allowed here: concatenating the spans recovers the
source, including its whitespace. A clause without a safe boundary stays whole
so the caller can reject its token budget instead of cutting a word.
"""
import re


VERSION = 1
DEFAULT_MAX_UNITS = 24
SENTENCE_ENDS = frozenset('.!?。！？')
CLAUSE_ENDS = frozenset(',;:，；：、')
CLOSERS = frozenset('"\'”’»」』）》】')
CJK = r'\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af'
WORD = r'[^\W_' + CJK + r']+'
UNITS = re.compile(r'[' + CJK + r']|' + WORD + r'(?:[\'’.-]' + WORD + r')*')


def semantic_units(text):
    return len(UNITS.findall(text))


def _punctuation_cuts(text, punctuation):
    cuts = []
    for index, char in enumerate(text):
        if char not in punctuation:
            continue
        before = text[index - 1] if index else ''
        after = text[index + 1] if index + 1 < len(text) else ''
        # Decimal points, thousands separators and numeric colon notation are
        # indivisible, as are ASCII punctuation characters inside a word.
        if before.isdecimal() and after.isdecimal():
            continue
        if char in '.!,;:?' and before.isalnum() and after.isalnum():
            continue
        end = index + 1
        while end < len(text) and (text[end] in CLOSERS or text[end] in punctuation):
            end += 1
        while end < len(text) and text[end].isspace():
            end += 1
        if end == len(text) or any(c.isalnum() for c in text[end:]):
            cuts.append(end)
    return sorted(set(cuts))


def _pieces(text, cuts):
    start = 0
    for end in sorted(set(cuts) | {len(text)}):
        if end > start:
            yield text[start:end]
            start = end


def _pack(pieces, maximum):
    current = ''
    for piece in pieces:
        if current and semantic_units(current + piece) > maximum:
            yield current
            current = ''
        current += piece
    if current:
        yield current


def _shorten(sentence, maximum):
    if semantic_units(sentence) <= maximum:
        return [sentence]
    clauses = list(_pieces(sentence, _punctuation_cuts(sentence, CLAUSE_ENDS)))
    pieces = []
    for clause in clauses:
        if semantic_units(clause) <= maximum:
            pieces.append(clause)
            continue
        # A whitespace boundary never separates digits in a grouped number.
        cuts = [match.end() for match in re.finditer(r'\s+', clause)
                if match.start() > 0 and match.end() < len(clause)
                and not (clause[match.start() - 1].isdecimal()
                         and clause[match.end()].isdecimal())]
        pieces.extend(_pack(_pieces(clause, cuts), maximum))
    return list(_pack(pieces, maximum))


def plan(text, maximum=DEFAULT_MAX_UNITS):
    """Return exact ordered source spans and a deterministic assembly contract."""
    if not isinstance(text, str) or not any(c.isalnum() for c in text):
        raise ValueError('Narration requires text with spoken content')
    if type(maximum) is not int or maximum < 1:
        raise ValueError('Narration segment limit must be a positive integer')
    pieces = [text]
    if semantic_units(text) > maximum:
        pieces = []
        for sentence in _pieces(text, _punctuation_cuts(text, SENTENCE_ENDS)):
            pieces.extend(_shorten(sentence, maximum))
    # Punctuation/whitespace without spoken content belongs to its neighbor.
    merged = []
    pending = ''
    for piece in pieces:
        if not any(c.isalnum() for c in piece):
            if merged:
                merged[-1] += piece
            else:
                pending += piece
        else:
            merged.append(pending + piece)
            pending = ''
    spans = []
    offset = 0
    for piece in merged:
        spans.append(dict(start=offset, end=offset + len(piece), text=piece))
        offset += len(piece)
    if ''.join(span['text'] for span in spans) != text:
        raise ValueError('Narration segmentation changed its source')
    return dict(version=VERSION, maximum_units=maximum, pause_ms=0,
                assembly='concatenate', spans=spans)
