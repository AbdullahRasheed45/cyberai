import importlib.util

spec = importlib.util.spec_from_file_location("provider_probe", "scripts/rental/provider_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_provider_cpu_or_wrong_device_cannot_be_accepted():
    assert probe.existing_environment_blockers("x86_64", {})
    assert probe.existing_environment_blockers(
        "aarch64",
        {
            "cuda": True,
            "bf16": True,
            "cuda_arithmetic": True,
            "fastmodel": True,
            "device": "H100",
            "capability": [9, 0],
            "errors": [],
            "versions": {},
        },
    )


def test_compatible_existing_environment_inventory():
    assert (
        probe.existing_environment_blockers(
            "aarch64",
            {
                "cuda": True,
                "bf16": True,
                "cuda_arithmetic": True,
                "fastmodel": True,
                "device": "NVIDIA GB10",
                "capability": [12, 1],
                "errors": [],
                "versions": {"torch": "2.10.0"},
            },
        )
        == []
    )


def test_probe_source_is_executable_python():
    compile(probe.GPU_PROBE, "provider_gpu_probe", "exec")
