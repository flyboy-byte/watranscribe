"""Map summary sentences to transcription timestamps for interactive playback.

Ported unchanged from the original summary_mapper.py — pure/stateless, no
framework dependency.
"""

import re
from typing import List, Dict, Tuple


def find_best_match_timestamp(summary_sentence: str, words: List[Dict], transcription: str) -> Tuple[float, float]:
    """Find the best timestamp range for a summary sentence by matching keywords.

    Args:
        summary_sentence: A sentence from the summary
        words: List of word objects with timestamps from Deepgram
        transcription: Full transcription text

    Returns:
        Tuple of (start_time, end_time) for the matched section
    """
    if not words or not summary_sentence:
        return (0.0, 0.0)

    summary_words = re.findall(r'\b\w+\b', summary_sentence.lower())
    summary_words = [w for w in summary_words if len(w) > 3]

    if not summary_words:
        return (0.0, 0.0)

    best_match_start = None
    best_match_end = None
    best_score = 0

    for i in range(len(words)):
        score = 0
        match_start = None
        match_end = None

        for j in range(i, min(i + 50, len(words))):
            word_text = words[j]['word'].lower()

            if word_text in summary_words:
                score += 1
                if match_start is None:
                    match_start = words[j]['start']
                match_end = words[j]['end']

        if score > best_score:
            best_score = score
            best_match_start = match_start
            best_match_end = match_end

    if best_match_start is not None and best_match_end is not None:
        return (best_match_start, best_match_end)

    return (0.0, words[-1]['end'] if words else 0.0)


def map_summary_to_timestamps(summary: str, words: List[Dict], transcription: str) -> List[Dict]:
    """Map each sentence in a summary to timestamps.

    Args:
        summary: The summary text
        words: List of word objects with timestamps
        transcription: Full transcription text

    Returns:
        List of dicts with 'text', 'start', and 'end' for each summary sentence
    """
    sentences = re.split(r'[.!?]+', summary)
    sentences = [s.strip() for s in sentences if s.strip()]

    mapped_sentences = []
    for sentence in sentences:
        start, end = find_best_match_timestamp(sentence, words, transcription)
        mapped_sentences.append({
            'text': sentence,
            'start': start,
            'end': end
        })

    return mapped_sentences


def map_conversation_summary_to_files(summary: str, file_data: List[Dict]) -> List[Dict]:
    """Map conversation summary sentences to specific files and timestamps.

    Args:
        summary: The conversation summary text
        file_data: List of dicts with 'file_name', 'words', and 'transcription'

    Returns:
        List of dicts with 'text', 'file_idx', 'start', and 'end'
    """
    sentences = re.split(r'[.!?]+', summary)
    sentences = [s.strip() for s in sentences if s.strip()]

    mapped_sentences = []
    for sentence in sentences:
        best_file_idx = 0
        best_start = 0.0
        best_end = 0.0
        best_score = 0

        for idx, file_info in enumerate(file_data):
            if not file_info.get('words'):
                continue

            start, end = find_best_match_timestamp(
                sentence,
                file_info['words'],
                file_info.get('transcription', '')
            )

            summary_words = re.findall(r'\b\w+\b', sentence.lower())
            summary_words = [w for w in summary_words if len(w) > 3]

            score = 0
            for word_obj in file_info['words']:
                if word_obj['word'].lower() in summary_words:
                    score += 1

            if score > best_score:
                best_score = score
                best_file_idx = idx
                best_start = start
                best_end = end

        mapped_sentences.append({
            'text': sentence,
            'file_idx': best_file_idx,
            'start': best_start,
            'end': best_end
        })

    return mapped_sentences
