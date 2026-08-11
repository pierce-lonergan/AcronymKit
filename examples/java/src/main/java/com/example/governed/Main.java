package com.example.governed;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * What a JVM service actually does with the governed subsystem: expand a schema's column names, and
 * find out which of them the catalog does not cover.
 *
 * <p>Four things are being demonstrated, in this order.
 *
 * <ol>
 *   <li><b>What it costs to start.</b> Printed first because it is the number that decides the
 *       shape of the integration. If starting the co-process were free you would start one per
 *       request; it is not, so you start one and hold it.
 *   <li><b>What the answers look like</b>, including the ones where the library declines to guess.
 *       An identifier that is not fully known is not an error — it is the library reporting that a
 *       token is missing from the vocabulary it was handed, which is the finding a governance team
 *       is actually after.
 *   <li><b>What it costs per name once warm</b>, over a corpus large enough that start-up is not
 *       what is being measured.
 *   <li><b>The same corpus under {@code --unknown reject}</b>, where an unmapped token stops being
 *       a note on the answer and becomes a failed record. Same library, same catalog, different
 *       governance stance.
 * </ol>
 *
 * <p>Run it with {@code mvn -q compile exec:java}. See README.md in this directory.
 */
public final class Main {

    private Main() {}

    /** Where the {@code acronymkit} executable is. Override with {@code -Dacronymkit.command=...}. */
    private static final String COMMAND = System.getProperty("acronymkit.command", "acronymkit");

    /**
     * Run the demonstration.
     *
     * @param args optionally the vocabulary directory, the identifier file, and how many times to
     *     repeat that file for the timed pass. Defaults are the files beside this project.
     * @throws IOException if the co-process cannot be started or dies mid-stream
     */
    public static void main(String[] args) throws IOException {
        Path vocabulary = Path.of(args.length > 0 ? args[0] : "vocabulary");
        Path corpus = Path.of(args.length > 1 ? args[1] : "identifiers.txt");
        int repeats = args.length > 2 ? Integer.parseInt(args[2]) : 250;

        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        List<String> identifiers = readSchema(corpus);

        out.printf("acronymkit command : %s%n", COMMAND);
        out.printf("vocabulary         : %s%n", vocabulary.toAbsolutePath());
        out.printf("identifiers        : %d from %s%n%n", identifiers.size(), corpus);

        expandTheSchema(out, vocabulary, identifiers, repeats);
        rejectInsteadOfReporting(out, vocabulary, identifiers);
    }

    /** The main pass: report what the catalog does and does not cover, then time it. */
    private static void expandTheSchema(
            PrintStream out, Path vocabulary, List<String> identifiers, int repeats)
            throws IOException {
        long startedAt = System.nanoTime();
        try (GovernedBatchClient client =
                GovernedBatchClient.start(COMMAND, vocabulary, "expand")) {

            List<BatchRecord> records = new ArrayList<>();
            records.add(client.expandOne(identifiers.get(0)));
            out.printf(
                    "cold start, spawn to first answer: %.1f ms%n%n",
                    (System.nanoTime() - startedAt) / 1e6);
            records.addAll(client.expand(identifiers.subList(1, identifiers.size())));

            report(out, records);

            Set<String> missing = new LinkedHashSet<>();
            for (BatchRecord record : records) {
                if (record.ok() && !record.result().isFullyKnown()) {
                    for (TokenExpansion token : record.result().tokens()) {
                        if (!token.isKnown()) {
                            missing.add(token.raw());
                        }
                    }
                }
            }
            out.printf(
                    "%ntokens this vocabulary does not cover: %s%n"
                        + "  Each one is a catalog row somebody has to write, or a column somebody"
                        + " has to rename.%n"
                        + "  The library will not invent an expansion for them, which is the point"
                        + " of it.%n",
                    missing);

            List<String> warm = new ArrayList<>(identifiers.size() * repeats);
            for (int i = 0; i < repeats; i++) {
                warm.addAll(identifiers);
            }
            long began = System.nanoTime();
            List<BatchRecord> answers = client.expand(warm);
            double elapsedMs = (System.nanoTime() - began) / 1e6;
            out.printf(
                    "%n%,d names once warm: %,.1f ms, %,.0f names/sec, %.2f us each%n",
                    answers.size(),
                    elapsedMs,
                    answers.size() / (elapsedMs / 1000.0),
                    elapsedMs * 1000.0 / answers.size());

            GovernedBatchClient.Summary summary = client.finish();
            out.printf(
                    "%nsummary line: op=%s records=%,d failed=%d skipped=%d exit=%d%n",
                    summary.op(),
                    summary.records(),
                    summary.failed(),
                    summary.skipped(),
                    summary.exitStatus());
            // Reconciling this is the reason the summary line exists. A pipeline that quietly lost
            // records is the failure that is hardest to notice and worst to find out about later.
            int sent = identifiers.size() + warm.size();
            out.printf(
                    "  sent %,d identifiers, the co-process answered %,d: %s%n",
                    sent, summary.records(), sent == summary.records() ? "reconciled" : "MISMATCH");
        }
    }

    /**
     * The same corpus with the other unknown-token stance.
     *
     * <p>Worth running once against your own catalog before choosing between them. Under
     * {@code reject} the exit status is 1 and the failed records name the token that caused it, so
     * a build step can fail a schema change that introduces an ungoverned abbreviation. Under the
     * default the same information arrives as a note on a successful answer, which is what a
     * reporting pass wants.
     */
    private static void rejectInsteadOfReporting(
            PrintStream out, Path vocabulary, List<String> identifiers) throws IOException {
        out.printf("%n--- the same schema under --unknown reject ---%n");
        try (GovernedBatchClient client =
                GovernedBatchClient.start(COMMAND, vocabulary, "expand", "reject")) {
            for (BatchRecord record : client.expand(identifiers)) {
                if (!record.ok()) {
                    out.printf("  %-20s [%s] %s%n", record.input(), record.errorType(),
                            firstSentence(record.error()));
                }
            }
            GovernedBatchClient.Summary summary = client.finish();
            out.printf(
                    "  %,d of %,d records failed; exit status %d%n",
                    summary.failed(), summary.records(), summary.exitStatus());
        }
    }

    /**
     * Read a schema slice.
     *
     * <p>The {@code #} comment convention belongs to this file, not to {@code governed-batch},
     * which has no comment syntax and would answer a comment line as a column name.
     */
    private static List<String> readSchema(Path corpus) throws IOException {
        return Files.readAllLines(corpus, StandardCharsets.UTF_8).stream()
                .map(String::strip)
                .filter(line -> !line.isEmpty() && !line.startsWith("#"))
                .toList();
    }

    private static void report(PrintStream out, List<BatchRecord> records) {
        for (BatchRecord record : records) {
            if (!record.ok()) {
                // A record that failed, as against a name that did not comply. Route on
                // errorType; the prose in error() is for a person and the contract does not fix it.
                out.printf(
                        "  %-20s FAILED [%s] %s%n",
                        record.input(), record.errorType(), firstSentence(record.error()));
                continue;
            }
            IdentifierExpansion expansion = record.result();
            out.printf(
                    "  %-20s %-34s %s%n",
                    expansion.identifier(),
                    expansion.phrase(),
                    expansion.isFullyKnown()
                            ? "fully governed"
                            : "not in catalog: " + unknownIn(expansion));
        }
    }

    private static String unknownIn(IdentifierExpansion expansion) {
        return expansion.tokens().stream()
                .filter(token -> !token.isKnown())
                .map(TokenExpansion::raw)
                .toList()
                .toString();
    }

    /** The error field is a paragraph for a person; one sentence of it fits a console table. */
    private static String firstSentence(String error) {
        int stop = error.indexOf(". ");
        return stop < 0 ? error : error.substring(0, stop + 1);
    }
}
