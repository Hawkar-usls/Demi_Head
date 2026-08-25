from probes.sovereign_lock_gate import make_proposal, make_approval, verify, consume

def test_hash_bound_and_replay(tmp_path):
    proposal=tmp_path/"candidate.py"; proposal.write_text("x=1\n")
    p=make_proposal(proposal,"restored/candidate.py")
    a=make_approval(p,approved_by_label="human-review",nonce="n-1")
    ledger=tmp_path/"consumed.jsonl"
    assert verify(proposal,"restored/candidate.py",a,ledger)["authorized"] is True
    proposal.write_text("x=2\n")
    assert verify(proposal,"restored/candidate.py",a,ledger)["reason"]=="proposal_hash_mismatch"
    proposal.write_text("x=1\n")
    consume(ledger,a,outcome="REVIEWED_NOT_AUTO_APPLIED")
    assert verify(proposal,"restored/candidate.py",a,ledger)["reason"]=="replay"

def test_target_binding(tmp_path):
    proposal=tmp_path/"candidate.py"; proposal.write_text("pass\n")
    p=make_proposal(proposal,"a.py"); a=make_approval(p,approved_by_label="reviewer",nonce="n")
    assert verify(proposal,"b.py",a)["reason"]=="target_mismatch"
