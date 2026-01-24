"""
Context Compressor for Agent Responses

Compresses and filters agent output before returning to Claude Code,
minimizing token usage while preserving essential information.
"""

import re
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class CompressionLevel(Enum):
    """Compression aggressiveness levels."""
    MINIMAL = "minimal"      # Light cleanup, preserve most content
    MODERATE = "moderate"    # Remove verbose explanations, keep code
    AGGRESSIVE = "aggressive"  # Only essential results and code


@dataclass
class CompressionConfig:
    """Configuration for context compression."""
    max_tokens: int = 2000
    preserve_code: bool = True
    preserve_errors: bool = True
    preserve_file_paths: bool = True
    remove_thinking: bool = True
    remove_verbose_explanations: bool = True
    summarize_long_outputs: bool = True


class ContextCompressor:
    """
    Compresses agent output to minimize token usage.

    Strategies:
    1. Remove verbose explanations and thinking
    2. Extract and preserve code blocks
    3. Preserve error messages and file paths
    4. Summarize lengthy prose sections
    5. Remove redundant whitespace and formatting
    """

    # Patterns for content extraction
    CODE_BLOCK_PATTERN = re.compile(r'```[\w]*\n(.*?)```', re.DOTALL)
    FILE_PATH_PATTERN = re.compile(r'(?:^|\s)([/\w.-]+\.[a-zA-Z]{1,5})(?:\s|$|:|\))')
    ERROR_PATTERN = re.compile(r'(?:error|exception|failed|failure|traceback)[:.\s].*', re.IGNORECASE)
    THINKING_PATTERN = re.compile(r'(?:I think|Let me|I\'ll|I will|First,|Now,|Then,|Finally,|Hmm|Actually,|Wait,).*?(?:\.|$)', re.IGNORECASE)

    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()

    def compress(
        self,
        content: str,
        level: CompressionLevel = CompressionLevel.MODERATE
    ) -> Dict[str, Any]:
        """
        Compress content based on the specified level.

        Returns a dict with:
        - compressed: The compressed content
        - code_blocks: Extracted code blocks
        - file_paths: Mentioned file paths
        - errors: Any error messages
        - summary: Brief summary if content was truncated
        - original_length: Original character count
        - compressed_length: Compressed character count
        """
        original_length = len(content)

        # Extract important elements
        code_blocks = self._extract_code_blocks(content)
        file_paths = self._extract_file_paths(content)
        errors = self._extract_errors(content)

        # Apply compression based on level
        if level == CompressionLevel.MINIMAL:
            compressed = self._minimal_compress(content)
        elif level == CompressionLevel.MODERATE:
            compressed = self._moderate_compress(content, code_blocks)
        else:  # AGGRESSIVE
            compressed = self._aggressive_compress(content, code_blocks, errors)

        # Final cleanup
        compressed = self._cleanup(compressed)

        # Truncate if still too long
        if len(compressed) > self.config.max_tokens * 4:  # ~4 chars per token estimate
            compressed = self._truncate_with_summary(compressed)

        return {
            "compressed": compressed,
            "code_blocks": code_blocks if self.config.preserve_code else [],
            "file_paths": list(file_paths) if self.config.preserve_file_paths else [],
            "errors": errors if self.config.preserve_errors else [],
            "original_length": original_length,
            "compressed_length": len(compressed),
            "compression_ratio": round(len(compressed) / original_length, 2) if original_length > 0 else 1.0
        }

    def _extract_code_blocks(self, content: str) -> List[str]:
        """Extract all code blocks from content."""
        return self.CODE_BLOCK_PATTERN.findall(content)

    def _extract_file_paths(self, content: str) -> set:
        """Extract file paths mentioned in content."""
        paths = set()
        for match in self.FILE_PATH_PATTERN.finditer(content):
            path = match.group(1)
            # Filter out common false positives
            if not path.startswith('.') and '/' in path:
                paths.add(path)
        return paths

    def _extract_errors(self, content: str) -> List[str]:
        """Extract error messages from content."""
        errors = []
        for match in self.ERROR_PATTERN.finditer(content):
            error = match.group(0).strip()
            if len(error) > 10:  # Filter very short matches
                errors.append(error[:500])  # Limit error length
        return errors[:5]  # Max 5 errors

    def _minimal_compress(self, content: str) -> str:
        """Light compression - mainly whitespace cleanup."""
        # Remove excessive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        # Remove trailing whitespace
        content = re.sub(r' +\n', '\n', content)
        return content.strip()

    def _moderate_compress(self, content: str, code_blocks: List[str]) -> str:
        """Moderate compression - remove verbose explanations, keep structure."""
        lines = content.split('\n')
        result_lines = []
        in_code_block = False

        for line in lines:
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                result_lines.append(line)
                continue

            # Always keep code
            if in_code_block:
                result_lines.append(line)
                continue

            # Remove thinking/planning phrases
            if self.config.remove_thinking and self.THINKING_PATTERN.match(line.strip()):
                continue

            # Remove very long explanation lines
            if self.config.remove_verbose_explanations and len(line) > 200:
                if not any(marker in line.lower() for marker in ['error', 'file', 'path', '`']):
                    continue

            result_lines.append(line)

        return '\n'.join(result_lines)

    def _aggressive_compress(
        self,
        content: str,
        code_blocks: List[str],
        errors: List[str]
    ) -> str:
        """Aggressive compression - only essential information."""
        parts = []

        # Add errors first if any
        if errors:
            parts.append("ERRORS:")
            parts.extend(f"- {e}" for e in errors[:3])

        # Add code blocks
        if code_blocks:
            parts.append("\nCODE:")
            for i, block in enumerate(code_blocks[:5], 1):
                # Truncate very long code blocks
                if len(block) > 1000:
                    block = block[:1000] + "\n... (truncated)"
                parts.append(f"```\n{block}\n```")

        # Extract key outcomes (lines with action words)
        outcome_patterns = [
            r'(?:created|modified|updated|deleted|added|removed|fixed|implemented|completed)\s+.*',
            r'(?:successfully|done|finished|completed).*',
        ]

        for pattern in outcome_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                outcome = match.group(0).strip()
                if len(outcome) < 200:
                    parts.append(f"- {outcome}")

        return '\n'.join(parts) if parts else self._moderate_compress(content, code_blocks)

    def _cleanup(self, content: str) -> str:
        """Final cleanup pass."""
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        # Remove empty bullet points
        content = re.sub(r'^\s*[-*]\s*$', '', content, flags=re.MULTILINE)
        return content.strip()

    def _truncate_with_summary(self, content: str) -> str:
        """Truncate content and add summary note."""
        max_chars = self.config.max_tokens * 4
        truncated = content[:max_chars]

        # Try to end at a natural break
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.8:
            truncated = truncated[:last_newline]

        return truncated + "\n\n[Output truncated - see full response in agent session]"


def compress_agent_output(
    output: str,
    level: str = "moderate",
    max_tokens: int = 2000
) -> Dict[str, Any]:
    """
    Convenience function to compress agent output.

    Args:
        output: Raw agent output string
        level: "minimal", "moderate", or "aggressive"
        max_tokens: Target maximum token count

    Returns:
        Dict with compressed content and metadata
    """
    config = CompressionConfig(max_tokens=max_tokens)
    compressor = ContextCompressor(config)

    level_enum = CompressionLevel(level)
    return compressor.compress(output, level_enum)


# FastAPI endpoint addition (add to router.py)
"""
Add this to router.py for the compression endpoint:

from context_compressor import compress_agent_output

class CompressRequest(BaseModel):
    content: str
    level: str = "moderate"  # minimal, moderate, aggressive
    max_tokens: int = 2000

class CompressResponse(BaseModel):
    compressed: str
    code_blocks: List[str]
    file_paths: List[str]
    errors: List[str]
    original_length: int
    compressed_length: int
    compression_ratio: float

@app.post("/compress", response_model=CompressResponse)
async def compress_content(request: CompressRequest) -> CompressResponse:
    result = compress_agent_output(
        request.content,
        level=request.level,
        max_tokens=request.max_tokens
    )
    return CompressResponse(**result)
"""


if __name__ == "__main__":
    # Test the compressor
    test_content = """
    I think I'll start by analyzing the codebase structure. Let me look at the files.

    First, I'll examine the main entry point. Actually, let me reconsider the approach.

    Here's the code I found:

    ```python
    def main():
        print("Hello World")
        return 0
    ```

    I modified the file at /src/main.py to add the new feature.

    The implementation is complete. I successfully added the authentication module.

    Error: Could not find config.json in the expected location.

    Let me now explain in great detail what each line does and why I chose this particular
    implementation pattern over the many alternatives that were available to me...
    """

    result = compress_agent_output(test_content, "aggressive")
    print("Compressed output:")
    print(result["compressed"])
    print(f"\nCompression ratio: {result['compression_ratio']}")
