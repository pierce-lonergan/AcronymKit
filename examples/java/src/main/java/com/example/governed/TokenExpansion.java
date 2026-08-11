package com.example.governed;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * One token of an expanded identifier.
 *
 * <p>Section 3 of {@code docs/notes/governed-json-contract.md} declares the field order and the
 * types; this record is a transcription of it and nothing more. Two of the fields need a Java
 * translation rather than a copy:
 *
 * <ul>
 *   <li>{@code long} is a Java keyword, so the field is named {@code longForm} and the wire name is
 *       restored with {@link JsonProperty}. This is the first thing that breaks in a hand-written
 *       mapper and it breaks silently — Jackson will happily leave a mis-named field null.
 *   <li>{@code confidence} is a JSON number that the reference implementation always writes with a
 *       decimal point ({@code 1.0}, {@code 0.0}). It is a {@code double}, not an {@code int}.
 * </ul>
 *
 * <p>{@link JsonIgnoreProperties} is deliberate and is the opposite of what the Python side does.
 * The library's own DTOs forbid extra keys, because an unrecognised key there means the caller
 * misunderstood the model. A consumer reading the wire wants the other rule: a future release that
 * adds a field should not stop this class parsing.
 *
 * @param raw the token exactly as it appeared in the identifier
 * @param longForm the governed long form, or a passthrough rendering when the token is unknown
 * @param isKnown whether the catalog (or an overlay) actually had a row for it
 * @param source where the answer came from — {@code governed}, {@code approved}, {@code custom},
 *     {@code scored}, {@code pinned} or {@code passthrough}
 * @param entryId the catalog row id, or null when nothing was matched
 * @param confidence the row's confidence; {@code 0.0} for a passthrough
 * @param classWord the class word this token supplies, when it is one
 * @param beat the candidates this answer outranked
 * @param kind the catalog row's kind
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record TokenExpansion(
        String raw,
        @JsonProperty("long") String longForm,
        @JsonProperty("is_known") boolean isKnown,
        String source,
        @JsonProperty("entry_id") String entryId,
        double confidence,
        @JsonProperty("class_word") String classWord,
        List<String> beat,
        String kind) {}
