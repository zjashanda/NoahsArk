"""Artifact digest/signature rejection before execution."""

from __future__ import annotations

from uuid import uuid4

from conftest import (
    FakeControlPlane,
    build_agent,
    flush_receipts,
    job_item,
    make_artifact,
    receipt_statuses,
)

from noahsark_node.protocol import assert_facts_only


def test_valid_signed_artifact_executes_and_reports_facts(
    tmp_path, signer
) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    lease_id = str(uuid4())
    artifact = make_artifact(b"frozen-bundle", signer)
    fake.polls.append([job_item(job_id=job_id, lease_id=lease_id, epoch=2, artifacts=[artifact])])

    report = agent.run_cycle()
    flush_receipts(agent, fake)

    assert report.jobs_executed == 1
    assert report.jobs_refused == 0
    assert receipt_statuses(fake, job_id) == ["started", "completed"]
    completed = next(
        receipt for receipt in fake.receipts if receipt["payload"]["status"] == "completed"
    )
    assert completed["payload"]["outcome"]["used_for_decision"] is False
    assert completed["payload"]["facts"]["artifact_checks"][0]["signature_verified"] is True
    assert "local_stop_confirmed" not in completed["payload"]["facts"]
    assert_facts_only(completed)


def test_digest_mismatch_is_refused_and_not_executed(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    artifact = make_artifact(b"tampered", signer, digest="0" * 64)
    fake.polls.append(
        [job_item(job_id=job_id, lease_id=str(uuid4()), epoch=1, artifacts=[artifact])]
    )

    report = agent.run_cycle()
    flush_receipts(agent, fake)

    assert report.jobs_refused == 1
    assert receipt_statuses(fake, job_id) == ["started", "rejected"]
    rejected = next(
        receipt for receipt in fake.receipts if receipt["payload"]["status"] == "rejected"
    )
    assert rejected["payload"]["error"]["code"] == "ARTIFACT_MISMATCH"
    assert rejected["payload"]["outcome"]["node_observed_execution_status"] == "NOT_STARTED"
    assert rejected["payload"]["outcome"]["node_observed_validity_status"] == "INVALID"
    assert "digest_mismatch" in rejected["payload"]["facts"]["artifact_check"]


def test_missing_signature_is_refused(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    artifact = make_artifact(b"unsigned", signer, signature=None)
    fake.polls.append(
        [job_item(job_id=job_id, lease_id=str(uuid4()), epoch=1, artifacts=[artifact])]
    )

    report = agent.run_cycle()
    flush_receipts(agent, fake)

    assert report.jobs_refused == 1
    rejected = next(
        receipt for receipt in fake.receipts if receipt["payload"]["status"] == "rejected"
    )
    assert "signature_missing" in rejected["payload"]["facts"]["artifact_check"]


def test_invalid_signature_is_refused(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    artifact = make_artifact(b"forged", signer, signature="not-a-valid-signature")
    fake.polls.append(
        [job_item(job_id=job_id, lease_id=str(uuid4()), epoch=1, artifacts=[artifact])]
    )

    report = agent.run_cycle()
    flush_receipts(agent, fake)

    assert report.jobs_refused == 1
    rejected = next(
        receipt for receipt in fake.receipts if receipt["payload"]["status"] == "rejected"
    )
    assert "signature_invalid" in rejected["payload"]["facts"]["artifact_check"]


def test_missing_artifact_content_is_refused(tmp_path, signer) -> None:
    fake = FakeControlPlane()
    agent = build_agent(tmp_path, fake, signer=signer)
    job_id = str(uuid4())
    artifact = make_artifact(b"lost", signer)
    artifact.pop("content_b64")
    fake.polls.append(
        [job_item(job_id=job_id, lease_id=str(uuid4()), epoch=1, artifacts=[artifact])]
    )

    report = agent.run_cycle()
    flush_receipts(agent, fake)

    assert report.jobs_refused == 1
    rejected = next(
        receipt for receipt in fake.receipts if receipt["payload"]["status"] == "rejected"
    )
    assert "artifact_missing" in rejected["payload"]["facts"]["artifact_check"]
