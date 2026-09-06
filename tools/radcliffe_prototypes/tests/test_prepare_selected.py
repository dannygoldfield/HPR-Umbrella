from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_selected import register_pending


class PendingSelectionTests(unittest.TestCase):
    def database(self):
        db=sqlite3.connect(":memory:");db.row_factory=sqlite3.Row
        root=Path(__file__).resolve().parents[3]
        db.executescript((root/"components/registry/src/hpr_registry/schema.sql").read_text())
        db.execute("INSERT INTO source_projects VALUES('SP','TEST','Test','now')")
        db.execute("INSERT INTO portraits(portrait_id,source_project_id,intake_filename,original_base_filename,portrait_group,created_at) VALUES('POR','SP','test.tif','test','age_100_plus','now')")
        db.execute("INSERT INTO portrait_revisions(revision_id,portrait_id,revision_number,file_path,sha256,file_size_bytes,metadata_manifest_path,created_at) VALUES('REV','POR',1,'test.tif','hash',1,'source.json','now')")
        db.execute("INSERT INTO visual_candidates(visual_id,portrait_id,revision_id,motion_recipe_id,duration_sec,seed,generator_version,manifest_path,created_at) VALUES('VIS','POR','REV','PDE-002',11,1,'1','v.json','now')")
        db.execute("INSERT INTO audio_candidates(audio_id,recipe_id,duration_sec,seed,generator_version,manifest_path,status,created_at) VALUES('AUD','AR-012',11,1,'1','a.json','banked','now')")
        db.execute("INSERT INTO candidate_reviews(subject_kind,subject_id,selected,notes,created_at) VALUES('audio','AUD',1,'original source approval','before')")
        db.commit();return db

    def item(self):
        return {"pairId":"PAIR","portraitId":"POR","visualId":"VIS","audioId":"AUD",
                "elevenSecondReference":{"path":"reference.mp4"},"manifestPath":"master.json",
                "projectLabel":"Test","option":1,"masterId":"MASTER","revisionId":"REV",
                "delivery":{"media":{"path":"delivery-33s.mp4"}}}

    def test_creative_selection_does_not_grant_loop_or_release_approval(self):
        db=self.database();register_pending(db,[self.item()],"now")
        master=db.execute("SELECT status,approved_at FROM final_masters").fetchone()
        self.assertEqual(("loop_pending",None),tuple(master))
        self.assertEqual("reserved_loop_pending",db.execute("SELECT status FROM audio_candidates").fetchone()[0])
        self.assertEqual("selected_loop_pending",db.execute("SELECT status FROM pair_candidates").fetchone()[0])
        self.assertEqual(1,db.execute("SELECT COUNT(*) FROM candidate_reviews WHERE subject_kind='audio'").fetchone()[0])
        self.assertEqual("original source approval",db.execute("SELECT notes FROM candidate_reviews WHERE subject_kind='audio'").fetchone()[0])

    def test_conflicting_selection_rolls_back_without_erasing_history(self):
        db=self.database()
        with self.assertRaises(ValueError):register_pending(db,[self.item(),self.item()],"now")
        self.assertEqual(0,db.execute("SELECT COUNT(*) FROM final_masters").fetchone()[0])
        self.assertEqual(0,db.execute("SELECT COUNT(*) FROM pair_candidates").fetchone()[0])
        self.assertEqual("banked",db.execute("SELECT status FROM audio_candidates").fetchone()[0])
        self.assertEqual(1,db.execute("SELECT COUNT(*) FROM candidate_reviews").fetchone()[0])


if __name__=="__main__":unittest.main()
