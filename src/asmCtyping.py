###############################################################################
# Exhaustive feature detection for x86-64 & ARM, can probably be toned-down.
###############################################################################
from __future__ import annotations

import ctypes
import platform
import sys
import subprocess
import re
from enum import Flag, auto
from functools import cached_property
from typing import List, Tuple, Optional
from pathlib import Path

# ------------------------------------------------------------------ helpers -- #
_IS_WIN = sys.platform == "win32"
_IS_LIN = sys.platform.startswith("linux")
_IS_MAC = sys.platform == "darwin"
_MACHINE = platform.machine().lower()
_IS_64BIT = sys.maxsize > 2**32


# ------------------------------------------------------------------ cpuid -- #
def _cpuid(leaf: int, subleaf: int = 0) -> Tuple[int, int, int, int]:
    """
    Portable CPUID implementation for x86/x86_64.
    Returns (eax, ebx, ecx, edx) or raises RuntimeError on non-x86.
    """
    if _MACHINE not in ("x86_64", "amd64", "x86", "i386", "i686"):
        raise RuntimeError(f"CPUID not supported on {_MACHINE}")

    # Structure to hold CPUID results
    class CPUIDResult(ctypes.Structure):
        _fields_ = [
            ("eax", ctypes.c_uint32),
            ("ebx", ctypes.c_uint32), 
            ("ecx", ctypes.c_uint32),
            ("edx", ctypes.c_uint32)
        ]

    result = CPUIDResult()

    if _IS_WIN:
        try:
            # Try to use __cpuidex from msvcrt (available in most Windows Python builds)
            msvcrt = ctypes.CDLL("msvcrt", use_errno=True)
            cpuidex = msvcrt.__cpuidex
            cpuidex.argtypes = [ctypes.POINTER(ctypes.c_int32), ctypes.c_int32, ctypes.c_int32]
            cpuidex.restype = None
            
            # Create array to hold results
            cpu_info = (ctypes.c_int32 * 4)()
            cpuidex(cpu_info, leaf, subleaf)
            
            return tuple(cpu_info)
            
        except (AttributeError, OSError):
            # Fallback: inline assembly via ctypes and shellcode
            if _IS_64BIT:
                # x64 inline assembly shellcode for CPUID
                shellcode = ctypes.create_string_buffer(
                    b"\x53"                    # push rbx
                    b"\x89\xc8"                # mov eax, ecx (leaf)
                    b"\x89\xd1"                # mov ecx, edx (subleaf)  
                    b"\x0f\xa2"                # cpuid
                    b"\x41\x89\x00"            # mov [r8], eax
                    b"\x41\x89\x58\x04"        # mov [r8+4], ebx
                    b"\x41\x89\x48\x08"        # mov [r8+8], ecx
                    b"\x41\x89\x50\x0c"        # mov [r8+12], edx
                    b"\x5b"                    # pop rbx
                    b"\xc3"                    # ret
                )
            else:
                # x86 inline assembly
                shellcode = ctypes.create_string_buffer(
                    b"\x53"                    # push ebx
                    b"\x8b\x44\x24\x08"        # mov eax, [esp+8] (leaf)
                    b"\x8b\x4c\x24\x0c"        # mov ecx, [esp+12] (subleaf)
                    b"\x0f\xa2"                # cpuid
                    b"\x8b\x54\x24\x10"        # mov edx, [esp+16] (result ptr)
                    b"\x89\x02"                # mov [edx], eax
                    b"\x89\x5a\x04"            # mov [edx+4], ebx
                    b"\x89\x4a\x08"            # mov [edx+8], ecx
                    b"\x89\x52\x0c"            # mov [edx+12], edx (from cpuid)
                    b"\x5b"                    # pop ebx
                    b"\xc3"                    # ret
                )
            
            # Make shellcode executable
            kernel32 = ctypes.windll.kernel32
            ptr = kernel32.VirtualAlloc(None, len(shellcode), 0x1000, 0x40)
            if not ptr:
                raise RuntimeError("Failed to allocate executable memory")
            
            ctypes.memmove(ptr, shellcode, len(shellcode))
            
            # Define function prototype and call
            if _IS_64BIT:
                func_type = ctypes.WINFUNCTYPE(None, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(CPUIDResult))
                func = func_type(ptr)
                func(leaf, subleaf, ctypes.byref(result))
            else:
                func_type = ctypes.WINFUNCTYPE(None, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(CPUIDResult))
                func = func_type(ptr)
                func(leaf, subleaf, ctypes.byref(result))
            
            kernel32.VirtualFree(ptr, 0, 0x8000)
            return (result.eax, result.ebx, result.ecx, result.edx)

    elif _IS_LIN:
        try:
            # Try GCC's __get_cpuid_count first (glibc >= 2.16)
            libc = ctypes.CDLL("libc.so.6")
            get_cpuid = libc.__get_cpuid_count
            get_cpuid.argtypes = [
                ctypes.c_uint32, ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)
            ]
            get_cpuid.restype = ctypes.c_int
            
            eax, ebx, ecx, edx = ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32()
            if get_cpuid(leaf, subleaf, ctypes.byref(eax), ctypes.byref(ebx), ctypes.byref(ecx), ctypes.byref(edx)):
                return (eax.value, ebx.value, ecx.value, edx.value)
                
        except (AttributeError, OSError):
            pass
        
        # Fallback: inline assembly for Linux
        try:
            if _IS_64BIT:
                # x86_64 inline assembly
                asm_code = f"""
                    .intel_syntax noprefix
                    .text
                    .globl _cpuid_func
                    _cpuid_func:
                        push rbx
                        mov eax, {leaf}
                        mov ecx, {subleaf}
                        cpuid
                        mov [rdi], eax
                        mov [rdi+4], ebx  
                        mov [rdi+8], ecx
                        mov [rdi+12], edx
                        pop rbx
                        ret
                """
            else:
                # x86 inline assembly  
                asm_code = f"""
                    .intel_syntax noprefix
                    .text
                    .globl _cpuid_func
                    _cpuid_func:
                        push ebx
                        push edi
                        mov eax, {leaf}
                        mov ecx, {subleaf}
                        cpuid
                        mov edi, [esp+12]
                        mov [edi], eax
                        mov [edi+4], ebx
                        mov [edi+8], ecx  
                        mov [edi+12], edx
                        pop edi
                        pop ebx
                        ret
                """
            
            # Compile and execute inline assembly
            import tempfile
            import os
            
            with tempfile.TemporaryDirectory() as tmpdir:
                asm_file = os.path.join(tmpdir, "cpuid.s")
                obj_file = os.path.join(tmpdir, "cpuid.o")
                so_file = os.path.join(tmpdir, "cpuid.so")
                
                with open(asm_file, 'w') as f:
                    f.write(asm_code)
                
                # Assemble and link
                subprocess.run(["as", "--64" if _IS_64BIT else "--32", "-o", obj_file, asm_file], check=True, capture_output=True)
                subprocess.run(["ld", "-shared", "-o", so_file, obj_file], check=True, capture_output=True)
                
                # Load and call
                lib = ctypes.CDLL(so_file)
                cpuid_func = lib._cpuid_func
                cpuid_func.argtypes = [ctypes.POINTER(CPUIDResult)]
                cpuid_func.restype = None
                
                cpuid_func(ctypes.byref(result))
                return (result.eax, result.ebx, result.ecx, result.edx)
                
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass

    # Ultimate fallback - return zeros (features will be detected via other methods)
    return (0, 0, 0, 0)


# ------------------------------------------------------------------ feature --
class CpuFeature(Flag):
    """Comprehensive CPU feature flags for x86_64 and ARM architectures."""
    
    # x86 Basic features
    MMX = auto()
    SSE = auto()
    SSE2 = auto()
    SSE3 = auto()
    SSSE3 = auto()
    SSE41 = auto()
    SSE42 = auto()
    POPCNT = auto()
    
    # x86 Crypto & Hash
    AES = auto()
    PCLMULQDQ = auto()
    SHA = auto()
    
    # x86 AVX family
    AVX = auto()
    AVX2 = auto()
    F16C = auto()
    FMA = auto()
    FMA4 = auto()
    
    # x86 AVX-512 family
    AVX512F = auto()
    AVX512CD = auto()
    AVX512BW = auto()
    AVX512DQ = auto()
    AVX512VL = auto()
    AVX512IFMA = auto()
    AVX512VBMI = auto()
    AVX512VBMI2 = auto()
    AVX512VPOPCNTDQ = auto()
    AVX512BITALG = auto()
    AVX512VNNI = auto()
    AVX512VP2INTERSECT = auto()
    AVX512FP16 = auto()
    
    # x86 Vector Neural Network Instructions
    AVXVNNI = auto()
    AVXIFMA = auto()
    AVXVNNIINT8 = auto()
    AVXNECONVERT = auto()
    
    # x86 Advanced Matrix Extensions
    AMXTILE = auto()
    AMXBF16 = auto()
    AMXINT8 = auto()
    AMXFP16 = auto()
    AMXCOMPLEX = auto()
    
    # x86 Bit Manipulation
    BMI1 = auto()
    BMI2 = auto()
    ABM = auto()  # Advanced Bit Manipulation
    TBM = auto()  # Trailing Bit Manipulation
    
    # x86 Random Number Generation
    RDRAND = auto()
    RDSEED = auto()
    
    # x86 Other extensions
    MOVBE = auto()
    ADX = auto()
    PREFETCHWT1 = auto()
    CLFLUSHOPT = auto()
    CLWB = auto()
    GFNI = auto()
    VAES = auto()
    VPCLMULQDQ = auto()
    
    # x86 Control Flow
    CET_IBT = auto()  # Intel CET Indirect Branch Tracking
    CET_SS = auto()   # Intel CET Shadow Stack
    
    # x86 Memory Protection
    MPX = auto()      # Memory Protection Extensions
    PKU = auto()      # Protection Keys for Userspace
    
    # ARM/AArch64 features
    NEON = auto()
    ASIMD = auto()    # Advanced SIMD
    SVE = auto()      # Scalable Vector Extension
    SVE2 = auto()     # SVE2
    
    # ARM Crypto
    ARM_AES = auto()
    ARM_SHA1 = auto()
    ARM_SHA2 = auto()
    ARM_SHA3 = auto()
    ARM_SHA512 = auto()
    ARM_SM3 = auto()
    ARM_SM4 = auto()
    
    # ARM Float16
    FPHP = auto()     # Half-precision floating-point
    ASIMDHP = auto()  # Advanced SIMD half-precision
    
    # ARM Dot Product
    ASIMDDP = auto()  # Advanced SIMD dot product
    
    # ARM Matrix
    SME = auto()      # Scalable Matrix Extension
    SME2 = auto()     # SME2
    
    # ARM Memory Tagging
    MTE = auto()      # Memory Tagging Extension
    
    # Basic flag
    BASIC = auto()

    # -------------------------------------------------------------- detection -- #
    @classmethod
    @cached_property  
    def _cached_features(cls) -> "CpuFeature":
        """Detect once and cache."""
        features = cls.BASIC
        
        if _MACHINE in ("x86_64", "amd64", "x86", "i386", "i686"):
            features |= cls._detect_x86_features()
        elif _MACHINE.startswith(("arm", "aarch")):
            features |= cls._detect_arm_features()
        
        return features

    @classmethod
    def detect(cls) -> "CpuFeature":
        """Get detected CPU features."""
        return cls._cached_features

    @classmethod
    def _detect_x86_features(cls) -> "CpuFeature":
        """Comprehensive x86/x86_64 feature detection."""
        features = cls.BASIC
        
        # Method 1: Use Windows IsProcessorFeaturePresent API
        if _IS_WIN:
            try:
                kernel32 = ctypes.windll.kernel32
                # Windows processor feature constants
                feature_map = {
                    0: cls.MMX,           # PF_MMX_INSTRUCTIONS_AVAILABLE
                    6: cls.SSE,           # PF_XMMI_INSTRUCTIONS_AVAILABLE  
                    10: cls.SSE2,         # PF_XMMI64_INSTRUCTIONS_AVAILABLE
                    13: cls.SSE3,         # PF_SSE3_INSTRUCTIONS_AVAILABLE
                    36: cls.SSSE3,        # PF_SSSE3_INSTRUCTIONS_AVAILABLE
                    37: cls.SSE41,        # PF_SSE4_1_INSTRUCTIONS_AVAILABLE
                    38: cls.SSE42,        # PF_SSE4_2_INSTRUCTIONS_AVAILABLE
                    39: cls.AVX,          # PF_AVX_INSTRUCTIONS_AVAILABLE
                    40: cls.AVX2,         # PF_AVX2_INSTRUCTIONS_AVAILABLE
                    41: cls.AVX512F,      # PF_AVX512F_INSTRUCTIONS_AVAILABLE
                }
                
                for pf_const, feature in feature_map.items():
                    try:
                        if kernel32.IsProcessorFeaturePresent(pf_const):
                            features |= feature
                    except (AttributeError, OSError):
                        continue
                        
            except Exception:
                pass

        # Method 2: CPUID detection (most comprehensive)
        try:
            # Get basic CPUID info
            max_leaf, vendor_b, vendor_d, vendor_c = _cpuid(0)
            vendor = struct.pack("<III", vendor_b, vendor_d, vendor_c).decode('ascii', errors='ignore')
            
            if max_leaf >= 1:
                eax, ebx, ecx, edx = _cpuid(1)
                
                # Feature flags from CPUID leaf 1
                # EDX register features
                if edx & (1 << 23): features |= cls.MMX
                if edx & (1 << 25): features |= cls.SSE
                if edx & (1 << 26): features |= cls.SSE2
                if edx & (1 << 28): features |= cls.HTT  # Hyper-Threading (if we add it)
                
                # ECX register features
                if ecx & (1 << 0):  features |= cls.SSE3
                if ecx & (1 << 1):  features |= cls.PCLMULQDQ
                if ecx & (1 << 9):  features |= cls.SSSE3
                if ecx & (1 << 12): features |= cls.FMA
                if ecx & (1 << 19): features |= cls.SSE41
                if ecx & (1 << 20): features |= cls.SSE42
                if ecx & (1 << 22): features |= cls.MOVBE
                if ecx & (1 << 23): features |= cls.POPCNT
                if ecx & (1 << 25): features |= cls.AES
                if ecx & (1 << 28): features |= cls.AVX
                if ecx & (1 << 29): features |= cls.F16C
                if ecx & (1 << 30): features |= cls.RDRAND
            
            # Extended features (CPUID leaf 7)
            if max_leaf >= 7:
                eax, ebx, ecx, edx = _cpuid(7, 0)
                
                # EBX register features  
                if ebx & (1 << 0):  features |= cls.FSGSBASE
                if ebx & (1 << 3):  features |= cls.BMI1
                if ebx & (1 << 5):  features |= cls.AVX2
                if ebx & (1 << 8):  features |= cls.BMI2
                if ebx & (1 << 14): features |= cls.MPX
                if ebx & (1 << 18): features |= cls.RDSEED
                if ebx & (1 << 19): features |= cls.ADX
                if ebx & (1 << 29): features |= cls.SHA
                
                # AVX-512 features
                if ebx & (1 << 16): features |= cls.AVX512F
                if ebx & (1 << 17): features |= cls.AVX512DQ
                if ebx & (1 << 21): features |= cls.AVX512IFMA
                if ebx & (1 << 26): features |= cls.AVX512PF
                if ebx & (1 << 27): features |= cls.AVX512ER
                if ebx & (1 << 28): features |= cls.AVX512CD
                if ebx & (1 << 30): features |= cls.AVX512BW
                if ebx & (1 << 31): features |= cls.AVX512VL
                
                # ECX register features
                if ecx & (1 << 1):  features |= cls.AVX512VBMI
                if ecx & (1 << 6):  features |= cls.AVX512VBMI2
                if ecx & (1 << 8):  features |= cls.GFNI
                if ecx & (1 << 9):  features |= cls.VAES
                if ecx & (1 << 10): features |= cls.VPCLMULQDQ
                if ecx & (1 << 11): features |= cls.AVX512VNNI
                if ecx & (1 << 12): features |= cls.AVX512BITALG
                if ecx & (1 << 14): features |= cls.AVX512VPOPCNTDQ
                
                # EDX register features
                if edx & (1 << 2):  features |= cls.AVX512FP16
                if edx & (1 << 8):  features |= cls.AVX512VP2INTERSECT
                
            # AMX features (CPUID leaf 7, subleaf 1)  
            if max_leaf >= 7:
                try:
                    eax, ebx, ecx, edx = _cpuid(7, 1)
                    if eax & (1 << 21): features |= cls.AMXTILE
                    if eax & (1 << 22): features |= cls.AMXINT8
                    if eax & (1 << 23): features |= cls.AMXBF16
                except:
                    pass
                
        except Exception:
            pass

        # Method 3: Linux /proc/cpuinfo fallback
        if _IS_LIN:
            try:
                cpuinfo = Path("/proc/cpuinfo").read_text()
                flags_line = ""
                for line in cpuinfo.splitlines():
                    if line.startswith("flags"):
                        flags_line = line
                        break
                
                flag_map = {
                    "mmx": cls.MMX,
                    "sse": cls.SSE,
                    "sse2": cls.SSE2,
                    "sse3": cls.SSE3,
                    "ssse3": cls.SSSE3,
                    "sse4_1": cls.SSE41,
                    "sse4_2": cls.SSE42,
                    "popcnt": cls.POPCNT,
                    "aes": cls.AES,
                    "pclmulqdq": cls.PCLMULQDQ,
                    "avx": cls.AVX,
                    "avx2": cls.AVX2,
                    "f16c": cls.F16C,
                    "fma": cls.FMA,
                    "fma4": cls.FMA4,
                    "movbe": cls.MOVBE,
                    "bmi1": cls.BMI1,
                    "bmi2": cls.BMI2,
                    "rdseed": cls.RDSEED,
                    "rdrand": cls.RDRAND,
                    "adx": cls.ADX,
                    "sha_ni": cls.SHA,
                    "avx512f": cls.AVX512F,
                    "avx512cd": cls.AVX512CD,
                    "avx512bw": cls.AVX512BW,
                    "avx512dq": cls.AVX512DQ,
                    "avx512vl": cls.AVX512VL,
                    "avx512ifma": cls.AVX512IFMA,
                    "avx512vbmi": cls.AVX512VBMI,
                    "avx512vbmi2": cls.AVX512VBMI2,
                    "avx512vpopcntdq": cls.AVX512VPOPCNTDQ,
                    "avx512bitalg": cls.AVX512BITALG,
                    "avx512vnni": cls.AVX512VNNI,
                    "gfni": cls.GFNI,
                    "vaes": cls.VAES,
                    "vpclmulqdq": cls.VPCLMULQDQ,
                    "avx_vnni": cls.AVXVNNI,
                    "amx_tile": cls.AMXTILE,
                    "amx_bf16": cls.AMXBF16,
                    "amx_int8": cls.AMXINT8,
                }
                
                for flag_name, feature in flag_map.items():
                    if flag_name in flags_line:
                        features |= feature
                        
            except (FileNotFoundError, PermissionError):
                pass

        return features

    @classmethod  
    def _detect_arm_features(cls) -> "CpuFeature":
        """ARM/AArch64 feature detection."""
        features = cls.BASIC
        
        if _IS_LIN:
            try:
                cpuinfo = Path("/proc/cpuinfo").read_text().lower()
                
                # Look for Features line in ARM /proc/cpuinfo
                features_line = ""
                for line in cpuinfo.splitlines():
                    if line.startswith("features"):
                        features_line = line
                        break
                
                flag_map = {
                    "neon": cls.NEON,
                    "asimd": cls.ASIMD,
                    "sve": cls.SVE,
                    "sve2": cls.SVE2,
                    "aes": cls.ARM_AES,
                    "sha1": cls.ARM_SHA1,
                    "sha2": cls.ARM_SHA2,
                    "sha3": cls.ARM_SHA3,
                    "sha512": cls.ARM_SHA512,
                    "sm3": cls.ARM_SM3,
                    "sm4": cls.ARM_SM4,
                    "fphp": cls.FPHP,
                    "asimdhp": cls.ASIMDHP,
                    "asimddp": cls.ASIMDDP,
                    "sme": cls.SME,
                    "sme2": cls.SME2,
                    "mte": cls.MTE,
                }
                
                for flag_name, feature in flag_map.items():
                    if flag_name in features_line:
                        features |= feature
                        
            except (FileNotFoundError, PermissionError):
                pass
        
        elif _IS_WIN:
            # Windows on ARM detection is limited
            # Use IsProcessorFeaturePresent for basic features
            try:
                kernel32 = ctypes.windll.kernel32
                # ARM processor features on Windows
                if kernel32.IsProcessorFeaturePresent(34):  # PF_ARM_NEON_INSTRUCTIONS_AVAILABLE
                    features |= cls.NEON
            except (AttributeError, OSError):
                pass
                
        return features

    # -------------------------------------------------------------- utilities -- #
    def names(self) -> List[str]:
        """Get list of feature names."""
        return [member.name for member in CpuFeature if member != CpuFeature.BASIC and member in self]

    def has_any(self, *features: 'CpuFeature') -> bool:
        """Check if any of the specified features are present."""
        return any(feature in self for feature in features)

    def has_all(self, *features: 'CpuFeature') -> bool:
        """Check if all of the specified features are present.""" 
        return all(feature in self for feature in features)

    def avx_level(self) -> int:
        """Get the highest AVX level supported (0, 1, 2, or 512)."""
        if self.AVX512F:
            return 512
        elif self.AVX2:
            return 2
        elif self.AVX:
            return 1
        else:
            return 0

    def sse_level(self) -> int:
        """Get the highest SSE level supported (0-4.2)."""
        if self.SSE42:
            return 4.2
        elif self.SSE41:
            return 4.1
        elif self.SSSE3:
            return 3.1  # SSSE3 is like SSE3.1
        elif self.SSE3:
            return 3.0
        elif self.SSE2:
            return 2.0
        elif self.SSE:
            return 1.0
        else:
            return 0.0

    def __str__(self) -> str:
        names = self.names()
        if not names:
            return "BASIC"
        return " | ".join(sorted(names))

    def __repr__(self) -> str:
        return f"CpuFeature({self})"
