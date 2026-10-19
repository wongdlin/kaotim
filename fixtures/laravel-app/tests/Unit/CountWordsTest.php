<?php

use App\Actions\CountWords;

it('AC-1: counts words separated by whitespace', function () {
    expect((new CountWords)->handle('one two  three'))->toBe(3);
});

it('EC-1: returns zero for blank input', function () {
    expect((new CountWords)->handle('   '))->toBe(0);
});
