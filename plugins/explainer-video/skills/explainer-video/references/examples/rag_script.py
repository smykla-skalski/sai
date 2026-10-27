"""Narration, one clip per beat: {scene class: [(clip key, spoken text), ...]}.

Keys are used in video.py. The text is only spoken, never shown, so it is written for
the ear. Cosine is written "co-sign" so the voice does not say "co-zeen"; HEARD maps
Whisper's spelling back for transcribe.py. Error codes are spoken as "E four
seventeen", and "near" replaces "close" (read as "clothes" in an earlier video).

Copyright 2026 Smykla Skalski, MIT License.
"""

from typing import Final

HEARD: Final = {"cosine": "co sign"}

BEATS: Final = {
    "Hook": [
        (
            "hook_1",
            (
                "You ask a chatbot a simple question about your company's product. Can "
                "I get a refund on an annual plan? It answers at once. It sounds sure. "
                "And it is wrong."
            ),
        ),
        (
            "hook_2",
            (
                "The model never read your refund policy. Everything it knows, it "
                "learned in training, months ago, from public text. So it guesses. How "
                "can it answer from your own documents instead?"
            ),
        ),
    ],
    "OpenBook": [
        (
            "book_1",
            (
                "Think of an exam. In a closed-book exam, you answer from memory. In "
                "an open-book exam, you look up the right page first, and then you "
                "answer."
            ),
        ),
        (
            "book_2",
            (
                "Retrieval augmented generation, or RAG, gives a language model an "
                "open-book exam. Retrieve the passages that match the question. "
                "Augment the prompt with them. Then generate the answer."
            ),
        ),
        (
            "book_3",
            (
                "Why not paste every document into the prompt? Ten thousand pages do "
                "not fit. And even when they do, you pay for every word, and the model "
                "gets worse at finding the one line that matters."
            ),
        ),
        (
            "book_4",
            (
                "And why not train the model on your documents? Training is slow and "
                "costly, it must run again after every change, and the model still "
                "cannot say where an answer came from."
            ),
        ),
    ],
    "Chunks": [
        (
            "chunk_1",
            (
                "RAG has two halves. The first runs ahead of time, before anyone asks. "
                "Take every document, and cut it into chunks, a few paragraphs each."
            ),
        ),
        (
            "chunk_2",
            (
                "Chunk size is a trade-off. A chunk that only says, within thirty "
                "days, has lost what it is about. A huge chunk mixes many topics, so "
                "it matches everything a little, and nothing well."
            ),
        ),
        (
            "chunk_3",
            (
                "So most systems use a few hundred words per chunk, and let neighbors "
                "overlap a little, so that a sentence cut at one edge is whole in the "
                "next chunk."
            ),
        ),
    ],
    "Embed": [
        (
            "emb_1",
            (
                "Next, an embedding model turns each chunk into a vector, a list of "
                "hundreds of numbers. Chunks with similar meaning get vectors that "
                "point the same way, even when they share no words."
            ),
        ),
        (
            "emb_2",
            (
                "The vectors go into an index, often called a vector database. This "
                "runs once per chunk, and again only for the chunks of a document that "
                "changes."
            ),
        ),
    ],
    "Query": [
        (
            "query_1",
            (
                "The second half runs for every question. Embed the question with the "
                "same model. It lands in the same space, near the chunks about the "
                "same topic."
            ),
        ),
    ],
    "Cosine": [
        (
            "cos_1",
            (
                "To score how near two vectors are, most systems use co-sign "
                "similarity. Draw each vector as an arrow, and look only at the angle "
                "between them. The same direction scores one. A right angle scores "
                "zero."
            ),
        ),
        (
            "cos_2",
            (
                "Here it is with small numbers. The question is point eight, point "
                "six. The refund chunk is point six, point eight. Multiply the "
                "matching numbers, and add them up. Point four eight plus point four "
                "eight is point nine six."
            ),
        ),
        (
            "cos_3",
            (
                "A password chunk, minus point six, point eight, scores zero. Most "
                "models make every vector one unit long, so the co-sign is just this "
                "sum, and an index can rank millions of chunks in milliseconds."
            ),
        ),
    ],
    "Prompt": [
        (
            "top_1",
            (
                "Keep the top few, here three chunks. They are the pages the model "
                "gets to read, and nothing else."
            ),
        ),
        (
            "aug_1",
            (
                "Now augment. Build the prompt in three parts: an instruction, the "
                "chunks, each with a source number, and the question at the end."
            ),
        ),
        (
            "aug_2",
            (
                "The instruction does real work. Answer only from the sources. Name "
                "the source you used. And if the sources do not say, answer: I don't "
                "know."
            ),
        ),
        (
            "gen_1",
            (
                "Then the model generates. It still writes every word, but it takes "
                "the facts from the page in front of it. Annual plans can be refunded "
                "within thirty days, source one."
            ),
        ),
    ],
    "Failure": [
        (
            "fail_1",
            ("Now let's break it. A user asks: what does error E four seventeen mean?"),
        ),
        (
            "fail_2",
            (
                "Vector search returns a page about error E four twelve, an overview "
                "of all error codes, and a page about timeouts. The page that explains "
                "E four seventeen is in fourth place, so it never reaches the prompt."
            ),
        ),
        (
            "fail_3",
            (
                "Embeddings capture meaning, not exact strings. To the model, E four "
                "seventeen and E four twelve mean almost the same thing: some error. "
                "So their vectors land almost on top of each other."
            ),
        ),
        (
            "fail_4",
            (
                "With the wrong pages in the prompt, the model says it does not know. "
                "Or worse, it explains the wrong error."
            ),
        ),
    ],
    "Hybrid": [
        (
            "fix_1",
            (
                "The fix is an old idea: keyword search. It scores chunks by the exact "
                "words they share with the question, and rare words, like E four "
                "seventeen, count the most."
            ),
        ),
        (
            "fix_2",
            (
                "Run both searches, and merge the two ranked lists. A chunk scores "
                "points for its rank in each list, so a page near the top of both "
                "rises. The E four seventeen page is back in the top three."
            ),
        ),
        (
            "fix_3",
            (
                "Many systems add one more step, a reranker. It reads the question and "
                "each candidate together, and sorts them again. Now the right page is "
                "first, and the model answers about the right error."
            ),
        ),
    ],
    "Dials": [
        (
            "dial_1",
            (
                "Each part of this has a dial. Send more chunks, and the answer is "
                "more likely to be in the prompt. But you also send more noise, pay "
                "more, and wait longer for the reply."
            ),
        ),
        (
            "dial_2",
            (
                "When a document changes, you embed its chunks again, and the next "
                "answer uses the new text. No retraining. The answers are only as "
                "fresh, and only as good, as the index."
            ),
        ),
        (
            "dial_3",
            (
                "Test the two halves on their own. For real questions, does the right "
                "chunk reach the top few? And does the answer say only what its "
                "sources say? Most bad answers start with bad retrieval."
            ),
        ),
    ],
    "Recap": [
        (
            "rec_1",
            (
                "So, back to our question. Can I get a refund on an annual plan? "
                "Search finds the refund policy. The prompt carries it, with a source "
                "number. And the model answers: yes, within thirty days, source one."
            ),
        ),
        (
            "rec_2",
            (
                "The model knows nothing new. It reads first, and then it answers. "
                "That is retrieval augmented generation."
            ),
        ),
    ],
}
