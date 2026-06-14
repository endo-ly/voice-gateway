"""Provider-agnostic speech segmenter for low-latency TTS."""

from app.domain.value_objects.speech_chunk import SpeechChunk
from app.domain.value_objects.speech_segment_policy import SpeechSegmentPolicy


class SpeechSegmenter:
    """Segments text into TTS-friendly chunks."""

    def segment(self, text: str, policy: SpeechSegmentPolicy) -> list[SpeechChunk]:
        if not text or not text.strip():
            return []

        raw_chunks = self._split(text, policy)
        if policy.merge_too_short_chunks:
            raw_chunks = self._merge_short_chunks(raw_chunks, policy)

        result: list[SpeechChunk] = []
        for i, chunk_text in enumerate(raw_chunks):
            stripped = chunk_text.strip()
            if not stripped:
                continue
            result.append(
                SpeechChunk(
                    index=len(result),
                    text=stripped,
                    tts_text=stripped,
                )
            )

        if result:
            self._shorten_first_chunk(result, policy)

        return result

    def _split(self, text: str, policy: SpeechSegmentPolicy) -> list[str]:
        strong_bounds = policy.split_punctuations
        soft_bounds = policy.soft_split_punctuations

        raw_segments = self._split_by_bounds(text, strong_bounds)

        refined: list[str] = []
        for seg in raw_segments:
            seg_stripped = seg.strip()
            if not seg_stripped:
                continue
            if len(seg_stripped) <= policy.normal_max_chars:
                refined.append(seg_stripped)
            else:
                refined.extend(self._split_long_segment(seg_stripped, policy, soft_bounds))

        return refined

    def _split_by_bounds(self, text: str, bounds: list[str]) -> list[str]:
        if not bounds:
            return [text]

        result: list[str] = []
        current = ""
        for char in text:
            current += char
            if char in bounds:
                result.append(current)
                current = ""
        if current:
            result.append(current)
        return result

    def _split_long_segment(
        self,
        segment: str,
        policy: SpeechSegmentPolicy,
        soft_bounds: list[str],
    ) -> list[str]:
        if len(segment) <= policy.normal_max_chars:
            return [segment]

        sub_parts = self._split_by_bounds(segment, soft_bounds)

        merged: list[str] = []
        current = ""
        for part in sub_parts:
            if len(current) + len(part) <= policy.normal_max_chars:
                current += part
            else:
                if current:
                    merged.append(current)
                current = part
        if current:
            merged.append(current)

        result: list[str] = []
        for chunk in merged:
            if len(chunk) <= policy.hard_max_chars:
                result.append(chunk)
            else:
                result.extend(self._force_split(chunk, policy.hard_max_chars))

        return result

    @staticmethod
    def _force_split(text: str, max_chars: int) -> list[str]:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    def _merge_short_chunks(
        self, chunks: list[str], policy: SpeechSegmentPolicy
    ) -> list[str]:
        if not chunks:
            return chunks

        merged: list[str] = []
        for chunk in chunks:
            if merged and len(chunk) < policy.min_chunk_chars:
                merged[-1] += chunk
            else:
                merged.append(chunk)

        if len(merged) >= 2 and len(merged[-1]) < policy.min_chunk_chars:
            merged[-2] += merged[-1]
            merged.pop()

        return merged

    def _shorten_first_chunk(
        self, chunks: list[SpeechChunk], policy: SpeechSegmentPolicy
    ) -> None:
        if not chunks:
            return
        if len(chunks[0].text) <= policy.first_chunk_max_chars:
            return

        soft_bounds = policy.soft_split_punctuations
        text = chunks[0].text

        best_pos = -1
        for i in range(policy.first_chunk_max_chars, min(policy.normal_max_chars, len(text))):
            if text[i] in soft_bounds:
                best_pos = i + 1
                break

        if best_pos < 0:
            for i in range(policy.first_chunk_max_chars, min(policy.normal_max_chars, len(text))):
                if text[i] == " ":
                    best_pos = i + 1
                    break

        if best_pos < 0:
            best_pos = policy.first_chunk_max_chars

        if best_pos > 0:
            first_text = text[:best_pos].strip()
            rest_text = text[best_pos:].strip()
            if rest_text:
                chunks[0] = SpeechChunk(index=0, text=first_text, tts_text=first_text)
                chunks.insert(
                    1, SpeechChunk(index=1, text=rest_text, tts_text=rest_text)
                )
                for i, chunk in enumerate(chunks):
                    chunk.index = i
