#include "prx/libSceLibreSsl3/libSceLibreSsl3.hpp"
#include "prx/libc/include/Api.hpp"
#include "prx/libc/include/ApplicationHeap.hpp"
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <memory>
#include <source_location>
#include <stdexcept>
#include <type_traits>

namespace {

using SetFlagsFunction = void (APS5_VABI *)(LibreSsl3CipherContext*, int);
static_assert(std::is_same_v<decltype(&EVP_CIPHER_CTX_set_flags_nid_postfix), SetFlagsFunction>);
static_assert(std::is_standard_layout_v<LibreSsl3CipherContext>);
static_assert(sizeof(LibreSsl3CipherContext) == 160);
static_assert(offsetof(LibreSsl3CipherContext, flags) == 104);
static_assert(sizeof(int) == 4);

struct GuardedContext {
    unsigned char before[16];
    LibreSsl3CipherContext context;
    unsigned char after[16];
};

void Require(bool condition, std::source_location location = std::source_location::current()) {
    if (condition) return;
    std::fprintf(stderr, "LibreSSL3 cipher flags check failed at line %u\n", location.line());
    std::abort();
}

void CheckFlags(GuardedContext& fixture, std::uint64_t initial, int flags, std::uint64_t expectedFlags) {
    std::memset(&fixture, 0xa5, sizeof(fixture));
    fixture.context.flags = initial;
    std::array<unsigned char, sizeof(fixture)> expected;
    std::memcpy(expected.data(), &fixture, sizeof(fixture));
    std::memcpy(expected.data() + offsetof(GuardedContext, context) + 104, &expectedFlags, sizeof(expectedFlags));
    const SetFlagsFunction setFlags = &EVP_CIPHER_CTX_set_flags_nid_postfix;
    setFlags(&fixture.context, flags);
    Require(std::memcmp(&fixture, expected.data(), sizeof(fixture)) == 0);
    setFlags(&fixture.context, flags);
    Require(std::memcmp(&fixture, expected.data(), sizeof(fixture)) == 0);
}

void CheckContext(GuardedContext& fixture) {
    CheckFlags(fixture, 0, 0, 0);
    CheckFlags(fixture, 1, 2, 3);
    CheckFlags(fixture, 0x0123456789abcdefULL, 0, 0x0123456789abcdefULL);
    CheckFlags(fixture, 0x8000000000000000ULL, 0x40000000, 0x8000000040000000ULL);
    CheckFlags(fixture, 0xdeadbeef00000000ULL, std::numeric_limits<int>::max(), 0xdeadbeef7fffffffULL);
    CheckFlags(fixture, 0, -1, 0xffffffffffffffffULL);
    CheckFlags(fixture, 0, std::numeric_limits<int>::min(), 0xffffffff80000000ULL);
    CheckFlags(fixture, 1, std::numeric_limits<int>::min() + 1, 0xffffffff80000001ULL);
    for (unsigned int bit = 0; bit < 32; ++bit) {
        const int flags = std::bit_cast<std::int32_t>(std::uint32_t{1} << bit);
        const auto expected = bit == 31 ? 0xffffffff80000001ULL : 0x1000000000000001ULL | (std::uint64_t{1} << bit);
        CheckFlags(fixture, 0x1000000000000001ULL, flags, expected);
    }
    CheckFlags(fixture, 0xa500000000000000ULL, 4, 0xa500000000000004ULL);
    EVP_CIPHER_CTX_set_flags_nid_postfix(&fixture.context, 0x20);
    Require(fixture.context.flags == 0xa500000000000024ULL);
    EVP_CIPHER_CTX_set_flags_nid_postfix(&fixture.context, 4);
    EVP_CIPHER_CTX_set_flags_nid_postfix(&fixture.context, 0);
    Require(fixture.context.flags == 0xa500000000000024ULL);
}

} // namespace

int main() {
    std::array<void*, 10> heapApi{};
    ApplicationHeapRegister_nid_no_patch(heapApi.data());
    GuardedContext stack{};
    CheckContext(stack);
    void* allocation = calloc_nid_postfix(1, sizeof(GuardedContext));
    Require(allocation != nullptr);
    auto* guest = std::construct_at(static_cast<GuardedContext*>(allocation));
    CheckContext(*guest);
    std::destroy_at(guest);
    free_nid_postfix(allocation);
    try {
        EVP_CIPHER_CTX_set_flags_nid_postfix(nullptr, 1);
        Require(false);
    } catch (const std::invalid_argument&) {
    }
    std::puts("libSceLibreSsl3 cipher flags tests passed");
}
