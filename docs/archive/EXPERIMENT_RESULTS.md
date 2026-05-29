/**
 * prependContext Format Experiment Results
 * =========================================
 * 
 * TypeScript Type Definition (from OpenClaw plugin-sdk):
 * ```typescript
 * type PluginHookBeforePromptBuildResult = {
 *   prependContext?: string;  // <-- MUST BE STRING
 *   ...
 * }
 * ```
 * 
 * OpenClaw Internal Processing:
 * 1. `concatOptionalTextSegments()` - uses template literal `${params.left}${separator}${params.right}`
 * 2. `joinPresentTextSegments()` - filters with `typeof segment !== "string"`
 * 3. Final usage: `effectivePrompt = \`${hookResult.prependContext}\n\n${params.prompt}\``
 * 
 * All of these expect prependContext to be a STRING.
 * 
 * EXPERIMENT RESULTS:
 * -------------------
 * Format 1: string
 *   - TypeScript: ✅ PASSES
 *   - OpenClaw: ✅ WORKS (expected format)
 * 
 * Format 2: message array [{ role: "system", content: [...] }]
 *   - TypeScript: ❌ FAILS - "Type '...' is not assignable to type 'string'"
 *   - OpenClaw: ⚠️ BROKEN - would be converted to "[object Object],..." string
 *   - Requires: `as any` to bypass TypeScript
 * 
 * Format 3: single message object { role: "system", content: "..." }
 *   - TypeScript: ❌ FAILS - "Type '...' is not assignable to type 'string'"
 *   - OpenClaw: ⚠️ BROKEN - would be converted to "[object Object]" string
 *   - Requires: `as any` to bypass TypeScript
 * 
 * Format 4: content block array [{ type: "text", text: "..." }]
 *   - TypeScript: ❌ FAILS - "Type '...' is not assignable to type 'string'"
 *   - OpenClaw: ⚠️ BROKEN - would be converted to "[object Object],..." string
 *   - Requires: `as any` to bypass TypeScript
 * 
 * CONCLUSION:
 * -----------
 * The ONLY correct format for prependContext is STRING.
 * 
 * The TypeScript types are correct - prependContext MUST be a string.
 * If you're seeing a "flatMap" error, it's likely NOT from prependContext itself,
 * but from some other part of the code that processes the hook result or messages.
 * 
 * RECOMMENDATION:
 * ---------------
 * Use Format 1 (string) - this is the only format that:
 * 1. Passes TypeScript compilation
 * 2. Works correctly with OpenClaw's internal processing
 * 3. Is documented in the OpenClaw plugin-sdk types
 * 
 * Example:
 * ```typescript
 * return {
 *   prependContext: `[LobsterPress Memory Context]\n${memoryContext}`,
 * };
 * ```
 */

// Test compilation of each format
type PluginHookBeforeAgentStartResult = {
  prependContext?: string;
  systemPrompt?: string;
};

// Format 1: String (CORRECT)
function format1_correct(): PluginHookBeforeAgentStartResult {
  return {
    prependContext: "[Memory Context]\nSome content here",
  };
}

// Format 2-4: Would need 'as any' but produce broken output
// These are shown for documentation purposes only
function format2_broken(): PluginHookBeforeAgentStartResult {
  // This returns garbage: "[object Object]"
  return {
    prependContext: [{ role: "system", content: "test" }] as any,
  };
}

export { format1_correct, format2_broken };
