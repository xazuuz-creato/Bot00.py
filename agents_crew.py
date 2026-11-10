import json

class MasterDirectorAgent:
    def __init__(self):
        self.role = "Senior Art Director & Quality Auditor"
        self.experience_years = 20

    def process_topic_to_uap(self, topic: str) -> str:
        uap_packet = {
            "sender": "MasterDirector_Agent",
            "receiver": "Visual_Generator_Agent",
            "protocol_version": "UAP/2.0",
            "directive": "Generate 3D Cinematic Motion Graphics",
            "content": topic,
            "cinematic_rules": {
                "color_palette": "Teal and Orange Cinematic Grade",
                "framing": "Rule of Thirds & Deep Bokeh Isolation",
                "camera_motion": "Smooth Pan / Spring Physics Zoom",
                "text_rendering": "Strict 100% Arabic BiDi Reshaped"
            },
            "status": "ready_for_rendering"
        }
        return json.dumps(uap_packet, ensure_ascii=False, indent=2)
