/** Strip vendor/model names from user-visible API text. */
export function sanitizeUserText(text: string | null | undefined): string | undefined {
  if (!text) return text ?? undefined;
  let out = text;
  const replacements: Array<[RegExp, string]> = [
    [/google\/[\w.-]+/gi, ""],
    [/gemini[\w.-]*/gi, "AI"],
    [/\breplicate\b/gi, "сервис анализа"],
    [/google[\s-]*ai[\s-]*studio/gi, "AI"],
    [/\bopenai\b|\bgpt-[\w.-]+|\bclaude\b|\banthropic\b/gi, "AI"],
    [/block_reason=\S+/gi, ""],
    [/blocked the input/gi, "не удалось обработать автоматически"],
    [/контент отклонён моделью[^.]*/gi, "требуется ручной просмотр"],
    [/direct gemini[^.]*/gi, ""],
  ];
  for (const [pattern, repl] of replacements) {
    out = out.replace(pattern, repl);
  }
  out = out.replace(/\s{2,}/g, " ").trim();
  return out || undefined;
}
