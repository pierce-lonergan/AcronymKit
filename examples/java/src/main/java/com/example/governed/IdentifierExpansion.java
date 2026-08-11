package com.example.governed;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * The answer for one physical name under {@code --op expand}.
 *
 * <p>The two fields worth reading carefully are {@code isFullyKnown} and {@code unaccounted},
 * because together they are the library's refusal to guess made machine-readable. {@code phrase}
 * always has a value: an unknown token is rendered by passthrough rather than invented. What tells
 * you the answer is partly a rendering rather than a governed expansion is {@code isFullyKnown}
 * being false — and then {@link TokenExpansion#isKnown()} says which tokens.
 *
 * <p>{@code unaccounted} is a different failure and is easy to conflate with the first.
 * It holds characters the tokenizer could not attribute to any token — an emoji or a stray symbol
 * inside a column name. A name can be fully known and have nothing unaccounted, fully known is not
 * implied by an empty {@code unaccounted}, and neither implies the name complies with the standard.
 * Compliance is a separate question, answered by {@code --op check}.
 *
 * @param identifier the physical name, echoed
 * @param phrase the whole expansion as one string
 * @param tokens the per-token detail, in identifier order
 * @param classWord the trailing class word, when the name has one
 * @param isFullyKnown whether every token resolved against the vocabulary
 * @param unaccounted characters the tokenizer could not attribute to a token
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record IdentifierExpansion(
        String identifier,
        String phrase,
        List<TokenExpansion> tokens,
        @JsonProperty("class_word") String classWord,
        @JsonProperty("is_fully_known") boolean isFullyKnown,
        List<String> unaccounted) {}
