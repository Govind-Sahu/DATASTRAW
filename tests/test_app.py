import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import main as app


class ReplyAssistantApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_db_path = app.DB_PATH
        app.DB_PATH = Path(cls.temp_dir.name) / "test.sqlite"
        app.initialize_db()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        app.DB_PATH = cls.original_db_path
        cls.temp_dir.cleanup()

    def request_json(self, path, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_brand_scoped_retrieval_returns_only_selected_brand_policy(self):
        with app.connect_db() as db:
            brands = {row["slug"]: row["id"] for row in db.execute("SELECT id, slug FROM brands")}
            northstar = app.retrieve_context(db, brands["northstar"], "My bottle is broken")
            tide = app.retrieve_context(db, brands["tide-timber"], "My bottle is broken")
            no_match = app.retrieve_context(db, brands["northstar"], "Do you have a loyalty rewards program?")

        self.assertTrue(northstar)
        self.assertTrue(tide)
        self.assertNotEqual(northstar[0]["content"], tide[0]["content"])
        self.assertIn("7 days", northstar[0]["content"])
        self.assertIn("5 days", tide[0]["content"])
        self.assertEqual(no_match, [])

    def test_model_guardrail_rejects_unapproved_commitments(self):
        context = [
            {
                "title": "Damaged items",
                "content": "Support will review the claim and confirm whether a refund is available.",
            }
        ]
        rejected = app.validate_model_draft(
            "We will issue you a refund today.", context
        )
        accepted = app.validate_model_draft(
            "Please send a photo. We will review the claim and confirm the available resolution.",
            context,
        )
        self.assertIn("unsupported refund promise", rejected)
        self.assertIsNone(accepted)

    def test_generate_edit_send_and_audit_log_round_trip(self):
        _, bootstrap = self.request_json("/api/bootstrap")
        conversation = next(item for item in bootstrap["conversations"] if item["brand_slug"] == "tide-timber")
        status, generated = self.request_json(
            "/api/generate", "POST", {"conversation_id": conversation["id"]}
        )
        self.assertEqual(status, 201)
        self.assertEqual(generated["provider"], "Grounded demo mode")
        self.assertIn("5 days", generated["draft"])
        self.assertTrue(any(item["category"] == "damaged_items" for item in generated["context"]))

        edited = generated["draft"] + " I have reviewed the details you shared."
        self.request_json(
            f"/api/reply-runs/{generated['run_id']}",
            "PUT",
            {"edited_response": edited},
        )
        _, sent = self.request_json(
            f"/api/reply-runs/{generated['run_id']}/send",
            "POST",
            {"final_response": edited},
        )
        self.assertEqual(sent["message"]["content"], edited)

        _, activity = self.request_json(f"/api/activity?conversation_id={conversation['id']}")
        run = activity["runs"][0]
        self.assertEqual(run["status"], "sent")
        self.assertEqual(run["generated_response"], generated["draft"])
        self.assertEqual(run["edited_response"], edited)
        self.assertEqual(run["final_response"], edited)
        self.assertTrue(run["sent_at"])

    def test_knowledge_base_crud_is_brand_scoped(self):
        _, bootstrap = self.request_json("/api/bootstrap")
        brand_id = next(item["id"] for item in bootstrap["brands"] if item["slug"] == "northstar")
        status, created = self.request_json(
            "/api/knowledge",
            "POST",
            {
                "brand_id": brand_id,
                "category": "loyalty",
                "title": "Loyalty program",
                "content": "Members earn points on eligible purchases.",
            },
        )
        self.assertEqual(status, 201)
        entry_id = created["entry"]["id"]
        self.request_json(
            f"/api/knowledge/{entry_id}",
            "PUT",
            {"category": "loyalty", "title": "Updated loyalty", "content": "Members earn points."},
        )
        _, updated_list = self.request_json(f"/api/knowledge?brand_id={brand_id}")
        updated = next(item for item in updated_list["entries"] if item["id"] == entry_id)
        self.assertEqual(updated["title"], "Updated loyalty")
        self.request_json(f"/api/knowledge/{entry_id}", "DELETE")
        _, final_list = self.request_json(f"/api/knowledge?brand_id={brand_id}")
        self.assertFalse(any(item["id"] == entry_id for item in final_list["entries"]))

    def test_double_send_of_same_draft_is_rejected(self):
        _, bootstrap = self.request_json("/api/bootstrap")
        conversation_id = bootstrap["conversations"][0]["id"]
        _, result = self.request_json("/api/generate", "POST", {"conversation_id": conversation_id})
        self.request_json(
            f"/api/reply-runs/{result['run_id']}/send",
            "POST",
            {"final_response": result["draft"]},
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request_json(
                f"/api/reply-runs/{result['run_id']}/send",
                "POST",
                {"final_response": result["draft"]},
            )
        self.assertEqual(error.exception.code, 409)


if __name__ == "__main__":
    unittest.main()
