import os
import shutil
import re

class TopicManager:
    """
    Manages the creation, reading, and saving of topic index files.
    """
    def __init__(self, base_dir='.'):
        """
        Initializes the TopicManager, ensuring necessary directories exist.
        """
        self.base_dir = base_dir
        self.topic_dir = os.path.join(self.base_dir, 'topic_memory')
        self.index_dir = os.path.join(self.topic_dir, 'indexes')
        self.template_path = os.path.join(self.topic_dir, 'templates', 'topic_template.txt')
        self.active_topics_dir = os.path.join(self.topic_dir, 'active_topics')

        os.makedirs(self.index_dir, exist_ok=True)
        os.makedirs(self.active_topics_dir, exist_ok=True)

    def _slugify(self, text):
        """
        Converts a string to a filesystem-friendly slug.
        e.g., "My New Topic" -> "my-new-topic"
        """
        text = text.lower()
        text = re.sub(r'[\s_]+', '-', text)  # Replace spaces and underscores with hyphens
        text = re.sub(r'[^\w-]', '', text)  # Remove non-alphanumeric characters except hyphens
        return text

    def get_all_topic_names(self):
        """
        Returns a list of all topic names (slugified filenames).
        """
        try:
            return [os.path.splitext(f)[0] for f in os.listdir(self.index_dir) if f.endswith('.txt')]
        except FileNotFoundError:
            return []

    def get_topic_content(self, topic_name_slug):
        """
        Loads and returns the content of a specific topic index file.
        """
        filepath = os.path.join(self.index_dir, f"{topic_name_slug}.txt")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return None

    def save_topic_content(self, topic_name_slug, content):
        """
        Saves content to a topic index file.
        """
        filepath = os.path.join(self.index_dir, f"{topic_name_slug}.txt")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    def create_new_topic(self, topic_display_name, alt_names=[]):
        """
        Creates a new topic index file from the template, populates the name,
        and saves it. Returns the slug of the new topic.
        """
        topic_slug = self._slugify(topic_display_name)
        filepath = os.path.join(self.index_dir, f"{topic_slug}.txt")

        if os.path.exists(filepath):
            # Topic already exists, do not overwrite
            return None

        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
        except FileNotFoundError:
            # If template is missing, we can't create a new topic
            return None

        content = template_content.replace('{{topic_name}}', topic_display_name)
        content = content.replace('{{list of all similar names for keyword search}}', ', '.join(alt_names))

        self.save_topic_content(topic_slug, content)
        return topic_slug

    def get_topic_search_data(self):
        """
        Parses all topics to get display names and alt names for searching.
        Returns a dict: {topic_slug: {'display_name': '...', 'alt_names': [...]}}
        """
        search_data = {}
        for topic_slug in self.get_all_topic_names():
            content = self.get_topic_content(topic_slug)
            if not content:
                continue

            display_name = "Unknown Topic"
            alt_names = []

            # Simple parser for the 'Key: value' format
            lines = content.split('\n')
            for line in lines:
                if line.startswith('Topic:'):
                    display_name = line.split(':', 1)[1].strip()
                elif line.startswith('Alt Names:'):
                    alt_names_str = line.split(':', 1)[1].strip()
                    if alt_names_str:
                        alt_names = [name.strip() for name in alt_names_str.split(',')]
                # Stop parsing after the first few lines for efficiency
                if line.startswith('Summary:'):
                    break

            search_data[topic_slug] = {
                'display_name': display_name,
                'alt_names': alt_names
            }
        return search_data

    def add_topics_to_active(self, topic_slugs):
        """
        Copies specified topic index files to the active_topics directory.
        """
        if not isinstance(topic_slugs, list):
            topic_slugs = [topic_slugs]

        for slug in topic_slugs:
            source_path = os.path.join(self.index_dir, f"{slug}.txt")
            dest_path = os.path.join(self.active_topics_dir, f"{slug}.txt")
            if os.path.exists(source_path):
                shutil.copy(source_path, dest_path)

    def get_active_topic_names(self):
        """
        Returns a list of topic names in the active_topics directory.
        """
        try:
            return [os.path.splitext(f)[0] for f in os.listdir(self.active_topics_dir) if f.endswith('.txt')]
        except FileNotFoundError:
            return []

    def clear_active_topics(self):
        """
        Removes all files from the active_topics directory.
        """
        for f in os.listdir(self.active_topics_dir):
            os.remove(os.path.join(self.active_topics_dir, f))
