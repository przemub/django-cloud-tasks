from unittest.mock import patch, ANY

from django.test import SimpleTestCase


class TaskViewTest(SimpleTestCase):
    def url(self, name):
        return f"/tasks/{name}"

    def test_task_called(self):
        data = {
            "price": 300,
            "quantity": 4,
            "discount": 0.2,
        }
        url = self.url(name="CalculatePriceTask")
        response = self.client.post(path=url, data=data, content_type="application/json")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"result": 960.0, "status": "executed"}, response.json())

    def test_task_called_with_internal_error(self):
        data = {
            "price": 300,
            "quantity": "wtf",
            "discount": 0.2,
        }
        url = self.url(name="CalculatePriceTask")
        with self.assertRaises(TypeError):
            self.client.post(path=url, data=data, content_type="application/json")

    def test_task_not_found(self):
        data = {}
        url = self.url(name="PotatoTask")
        response = self.client.post(path=url, data=data)
        self.assertEqual(404, response.status_code)

        expected_response = {
            "error": "Task PotatoTask not found",
        }
        self.assertEqual(expected_response, response.json())

    def test_task_called_with_get(self):
        url = self.url(name="CalculatePriceTask")
        response = self.client.get(path=url)
        self.assertEqual(405, response.status_code)

    def test_task_called_with_put(self):
        data = {}
        url = self.url(name="CalculatePriceTask")
        response = self.client.put(path=url, data=data)
        self.assertEqual(405, response.status_code)

    def test_task_called_with_delete(self):
        url = self.url(name="CalculatePriceTask")
        response = self.client.delete(path=url)
        self.assertEqual(405, response.status_code)

    def test_nested_task_called(self):
        data = {
            "name": "you",
        }
        url = self.url(name="OneBigDedicatedTask")
        response = self.client.post(path=url, data=data, content_type="application/json")
        self.assertEqual(200, response.status_code)
        self.assertEqual({"result": "Chuck Norris is better than you", "status": "executed"}, response.json())

    def test_propagate_headers(self):
        data = {
            "price": 10,
            "quantity": 42,
        }
        headers = {
            "traceparent": "trace-this-potato",
            "another-random-header": "please-do-not-propagate-this",
        }

        url = self.url(name="ParentCallingChildTask")
        django_headers = {f"HTTP_{key.upper()}": value for key, value in headers.items()}

        with patch("gcp_pilot.tasks.CloudTasks.push") as push:
            with patch("django_cloud_tasks.tasks.TaskMetadata.from_task_obj"):
                self.client.post(path=url, data=data, content_type="application/json", **django_headers)

        expected_kwargs = {
            "queue_name": "tasks",
            "url": "http://localhost:8080/tasks/CalculatePriceTask",
            "payload": '{"price": 10, "quantity": 42, "discount": 0}',
            "headers": {"Traceparent": "trace-this-potato", "X-CloudTasks-Projectname": ANY},
        }
        push.assert_called_once_with(**expected_kwargs)

    def test_absorb_headers(self):
        data = {}
        headers = {
            "traceparent": "trace-this-potato",
            "another-random-header": "please-do-not-propagate-this",
        }

        url = self.url(name="ExposeCustomHeadersTask")
        django_headers = {f"HTTP_{key.upper()}": value for key, value in headers.items()}

        response = self.client.post(path=url, data=data, content_type="application/json", **django_headers)

        expected_content = {"Traceparent": "trace-this-potato"}
        self.assertEqual(expected_content, response.json()["result"])
