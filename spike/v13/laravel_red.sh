#!/usr/bin/env bash
# Spike V13 / Appendix C.3: how Pest and PHPUnit (via `php artisan test`) report
# assertion failures vs. wrong-reason errors, with and without laravel/pao.
# Usage: spike/v13/laravel_red.sh <fixture-dir> <out-dir>
set -uo pipefail
src=$(cd "$1" && pwd); out=$2; mkdir -p "$out"
work=$(mktemp -d); cp -a "$src/." "$work/"; cd "$work"
[ -f .env.testing ] || cp .env.example .env.testing
if [ -f tests/Pest.php ]; then
cat > tests/Unit/RedTest.php <<'PHP'
<?php
it('AC-9: assertion failure', function () { expect(1 + 1)->toBe(3); });
it('AC-8: missing class', function () { expect((new App\Actions\DoesNotExist)->handle())->toBe(1); });
it('AC-7: undefined method', function () { expect((new App\Actions\CountWords)->nope())->toBe(1); });
PHP
else
cat > tests/Unit/RedTest.php <<'PHP'
<?php
namespace Tests\Unit;
use PHPUnit\Framework\TestCase;
class RedTest extends TestCase {
    public function test_ac_9_assertion_failure(): void { $this->assertSame(3, 1 + 1); }
    public function test_ac_8_missing_class(): void { $this->assertSame(1, (new \App\Actions\DoesNotExist)->handle()); }
    public function test_ac_7_undefined_method(): void { $this->assertSame(1, (new \App\Actions\CountWords)->nope()); }
}
PHP
fi
php artisan test tests/Unit/RedTest.php --log-junit "$out/junit.xml" > "$out/pao.txt" 2>&1; echo "exit(pao)=$?" >> "$out/exit.txt"
PAO_DISABLE=1 php artisan test tests/Unit/RedTest.php --no-ansi > "$out/plain.txt" 2>&1; echo "exit(plain)=$?" >> "$out/exit.txt"
# syntax error file: collection-level error
printf '<?php\nit("AC-6: syntax", function () { expect(1)->toBe(1) }\n' > tests/Unit/SyntaxTest.php
php artisan test tests/Unit/SyntaxTest.php --log-junit "$out/junit-syntax.xml" > "$out/syntax-pao.txt" 2>&1; echo "exit(syntax)=$?" >> "$out/exit.txt"
rm -rf "$work"
