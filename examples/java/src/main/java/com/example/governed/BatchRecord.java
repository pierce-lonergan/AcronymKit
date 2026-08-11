package com.example.governed;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * One line of {@code governed-batch}'s standard output: the envelope, not the answer.
 *
 * <p>Section 7.2 of the wire contract specifies this shape. The distinction it insists on, and the
 * one a Java caller most often gets wrong, is between a record that <em>failed</em> and a name that
 * did not <em>comply</em>. A failure sets {@code ok} false and fills {@code error} and
 * {@code errorType}; a non-compliant name arrives with {@code ok} true and the finding inside
 * {@code result}. Only the first affects the process exit status.
 *
 * <p>Route on {@code errorType}, never on {@code error}. The contract says in as many words that
 * {@code error} is prose for a person and is not part of the contract, so a port is free to reword
 * it. {@code errorType} is either the raised exception's class name or the literal
 * {@code "InputError"} for a line that could not be read at all.
 *
 * @param line the 1-based input line number, counting blank lines that produced no record. Under a
 *     long-lived co-process this keeps climbing across calls: it counts lines the process has read,
 *     not lines in any one request.
 * @param id whatever the request put in {@code id}, echoed untouched — a String, a number or a
 *     boolean, which is why it is typed as Object. Absent when the request supplied none.
 * @param input the subject as read, or the raw line when the line could not be read
 * @param ok whether the record carries an answer
 * @param result the answer, when {@code ok}; null otherwise. Typed to the {@code --op expand}
 *     payload — a client using another op wants a different type here.
 * @param error one sentence of prose, when not {@code ok}
 * @param errorType the exception class name, or {@code "InputError"}
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record BatchRecord(
        int line,
        Object id,
        String input,
        boolean ok,
        IdentifierExpansion result,
        String error,
        @JsonProperty("error_type") String errorType) {}
