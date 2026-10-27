"""Narration, one clip per beat. Keys are referenced from video.py.

The text is only spoken, so words the voice gets wrong are spelled by sound ("co-sign"
for cosine).

Copyright 2026 Smykla Skalski, MIT License.
"""

from typing import Final

BEATS: Final = {
    "Intro": [
        (
            "intro_1",
            (
                "Imagine ten thousand pages of documentation. Someone asks a question, "
                "and somewhere in there, one paragraph holds the answer."
            ),
        ),
        (
            "intro_2",
            (
                "A language model can write a great reply, but only if you hand it the "
                "right paragraph first. That is the idea behind retrieval augmented "
                "generation, or RAG."
            ),
        ),
        (
            "intro_3",
            (
                "So the real question is this. How does a computer find text that "
                "means the same thing as your question, even when it uses completely "
                "different words? The answer comes in two parts. Embeddings... and "
                "reranking."
            ),
        ),
    ],
    "Embeddings": [
        (
            "emb_1",
            (
                "Let's start with a strange idea. What if every piece of text could be "
                "a point in space?"
            ),
        ),
        (
            "emb_2",
            (
                "Not placed at random, but placed so that things with similar meanings "
                "land close together. Cat sits near kitten and dog. Car sits near "
                "truck and bus. And pizza ends up somewhere else entirely."
            ),
        ),
        (
            "emb_3",
            (
                "This mapping, from text to a point, is called an embedding. And a "
                "point is really just a list of numbers. Its coordinates."
            ),
        ),
        (
            "emb_4",
            (
                "Here we have two dimensions, so two numbers. Real embedding models "
                "use far more, typically somewhere between a few hundred and a few "
                "thousand. We can't picture that many dimensions, but the geometry "
                "works the same way. Close means similar."
            ),
        ),
        (
            "emb_5",
            (
                "In classic word embeddings, even directions carry meaning. The step "
                "from man to woman points roughly the same way as the step from king "
                "to queen. Nobody programmed that in. It simply falls out of training."
            ),
        ),
    ],
    "Training": [
        (
            "train_1",
            (
                "So where do these numbers come from? An embedding model is a neural "
                "network, usually a transformer, much like the ones inside chatbots."
            ),
        ),
        (
            "train_2",
            (
                "Text goes in and gets split into tokens. Each token flows through "
                "layers of attention, and comes out as its own vector. Then the model "
                "squeezes all of them into one, often by simply averaging. One "
                "fixed-size list of numbers, no matter how long the input was."
            ),
        ),
        (
            "train_3",
            (
                "To train it, you show the model pairs that belong together. A "
                "question and its answer. A title and its article. The model learns to "
                "pull each pair close together..."
            ),
        ),
        (
            "train_4",
            (
                "...and to push apart everything that doesn't match. Repeat this over "
                "hundreds of millions of examples, and the space organizes itself by "
                "meaning. This is called contrastive learning."
            ),
        ),
    ],
    "Similarity": [
        (
            "sim_1",
            (
                "Now, how do we measure closeness? The most common choice is co-sign "
                "similarity. Think of each embedding as an arrow, starting at the "
                "origin."
            ),
        ),
        (
            "sim_2",
            (
                "We ignore how long the arrows are, and look only at the angle between "
                "them. Arrows that point the same way score close to one."
            ),
        ),
        (
            "sim_3",
            (
                "At a right angle, the score is zero. Unrelated. Pointing in opposite "
                "directions, minus one."
            ),
        ),
        (
            "sim_4",
            (
                "To compute it, take the dot product. Multiply the matching "
                "coordinates, and add everything up. Then divide by the two lengths. "
                "Most models already normalize their vectors to length one, so in "
                "practice it's just the dot product. Cheap, fast, and easy to do "
                "millions of times."
            ),
        ),
    ],
    "Rag": [
        (
            "rag_1",
            (
                "Now we can build a search engine. First, the offline part. Take your "
                "documents, and cut them into chunks, maybe a few paragraphs each."
            ),
        ),
        (
            "rag_2",
            (
                "Run every chunk through the embedding model, once, and store the "
                "vectors in an index. This is what people call a vector database."
            ),
        ),
        (
            "rag_3",
            (
                "When a question arrives, embed it with the same model. It lands "
                "somewhere in that same space."
            ),
        ),
        (
            "rag_4",
            (
                "Then find its nearest neighbors. With millions of vectors, checking "
                "every single one is slow, so vector databases use approximate nearest "
                "neighbor search. Clever index structures that find the closest points "
                "in milliseconds."
            ),
        ),
        (
            "rag_5",
            (
                "Take the top few chunks, paste them into the prompt, and the language "
                "model writes its answer from them. That's RAG, in one picture."
            ),
        ),
    ],
    "Problem": [
        (
            "prob_1",
            (
                "But there's a catch. Here's a question. How do I cancel my "
                "subscription?"
            ),
        ),
        (
            "prob_2",
            (
                "And here are the chunks that vector search returned, ranked by "
                "similarity."
            ),
        ),
        (
            "prob_3",
            (
                "The chunk that actually answers the question is in third place. The "
                "top hit just shares the right words, and the right topic."
            ),
        ),
        (
            "prob_4",
            (
                "Why does this happen? The embedding model compresses every chunk into "
                "one vector before it ever sees your question. It has to guess, in "
                "advance, what matters about that chunk. The question and the chunk "
                "never actually meet."
            ),
        ),
    ],
    "Rerank": [
        (
            "rr_1",
            (
                "This is where reranking comes in. A reranker is usually a different "
                "kind of model, called a cross-encoder."
            ),
        ),
        (
            "rr_2",
            (
                "An embedding model is a bi-encoder. The query and the document each "
                "go through the model separately, and we only compare their vectors at "
                "the very end."
            ),
        ),
        (
            "rr_3",
            (
                "A cross-encoder reads the query and the document together, as one "
                "input. Every word in the question can pay attention to every word in "
                "the document."
            ),
        ),
        (
            "rr_4",
            (
                "So it can notice that cancel, here, is an action you want to take, "
                "not a marketing promise. And instead of a vector, it outputs one "
                "number. How relevant is this document to this question?"
            ),
        ),
        (
            "rr_5",
            (
                "Run it on each candidate, sort by the new scores, and the real answer "
                "jumps to the top."
            ),
        ),
    ],
    "Cost": [
        (
            "cost_1",
            (
                "So why not use the cross-encoder for everything? Because nothing can "
                "be computed ahead of time. Its score depends on the query, so every "
                "new question means one full model pass for every document."
            ),
        ),
        (
            "cost_2",
            (
                "Against ten million chunks, that's ten million passes for a single "
                "question. Far too slow."
            ),
        ),
        (
            "cost_3",
            (
                "Embeddings flip the trade-off. Documents are embedded once, ahead of "
                "time. A query costs one model pass, plus a fast index lookup."
            ),
        ),
        (
            "cost_4",
            (
                "So we use both, as a funnel. Vector search narrows millions of chunks "
                "down to maybe a hundred candidates. Fast, but rough. The reranker "
                "reads those hundred carefully, and keeps the best five. And those "
                "five go to the language model."
            ),
        ),
    ],
    "Outro": [
        (
            "out_1",
            (
                "That's the whole pattern. Embeddings turn meaning into geometry, so "
                "you can search by distance. They're built for recall. Cast a wide "
                "net, quickly."
            ),
        ),
        (
            "out_2",
            (
                "Reranking brings precision. Look closely at the few, with the "
                "question in hand."
            ),
        ),
        (
            "out_3",
            (
                "Fast and rough, then slow and careful. And your language model gets "
                "the paragraph it actually needs."
            ),
        ),
    ],
}
