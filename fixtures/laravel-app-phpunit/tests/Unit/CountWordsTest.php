<?php

namespace Tests\Unit;

use App\Actions\CountWords;
use PHPUnit\Framework\TestCase;

class CountWordsTest extends TestCase
{
    /** AC-1 */
    public function test_ac_1_counts_words_separated_by_whitespace(): void
    {
        $this->assertSame(3, (new CountWords)->handle("one two  three"));
    }

    /** EC-1 */
    public function test_ec_1_returns_zero_for_blank_input(): void
    {
        $this->assertSame(0, (new CountWords)->handle('   '));
    }
}
