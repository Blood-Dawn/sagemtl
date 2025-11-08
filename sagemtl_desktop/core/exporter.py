"""
Export cleaned/translated text to files.
"""

from pathlib import Path
from typing import List
from .models import Job, JobStatus


class Exporter:
    """Export cleaned/translated text to files"""

    def export_job(self, job: Job, output_dir: str) -> str:
        """
        Export a single job's cleaned text.

        Args:
            job: Job to export
            output_dir: Output directory

        Returns:
            Path to exported file

        Raises:
            ValueError: If job has no cleaned text
            OSError: If file cannot be written
        """
        if not job.cleaned_text:
            raise ValueError(f"Job {job.name} has no cleaned text to export")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        base_name = Path(job.name).stem
        filename = f"{base_name}_cleaned.txt"

        # Avoid overwriting - add number suffix if needed
        file_path = output_path / filename
        counter = 1
        while file_path.exists():
            filename = f"{base_name}_cleaned_{counter}.txt"
            file_path = output_path / filename
            counter += 1

        # Write cleaned text
        try:
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                # Add header
                f.write(f"# Cleaned/Translated: {job.name}\n")
                f.write(f"# Processed: {job.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Source Language: {job.metadata.get('source_lang', 'unknown')}\n")
                f.write(f"# Target Language: {job.metadata.get('target_lang', 'unknown')}\n")
                f.write("\n" + "="*80 + "\n\n")

                # Write cleaned text
                f.write(job.cleaned_text)

                # Add footer
                f.write("\n\n" + "="*80 + "\n")
                f.write(f"# End of {job.name}\n")

        except OSError as e:
            raise OSError(f"Failed to write file {file_path}: {e}")

        return str(file_path)

    def export_batch(self, jobs: List[Job], output_dir: str) -> List[str]:
        """
        Export multiple jobs.

        Args:
            jobs: List of jobs to export
            output_dir: Output directory

        Returns:
            List of exported file paths

        Raises:
            ValueError: If no jobs have cleaned text
        """
        exported = []
        skipped = []

        for job in jobs:
            # Only export completed jobs with cleaned text
            if job.status == JobStatus.COMPLETED and job.cleaned_text:
                try:
                    path = self.export_job(job, output_dir)
                    exported.append(path)
                except Exception as e:
                    print(f"Failed to export {job.name}: {e}")
                    skipped.append(job.name)
            else:
                skipped.append(job.name)

        if skipped:
            print(f"Skipped {len(skipped)} jobs: {', '.join(skipped[:5])}")

        return exported

    def export_job_as_text(self, job: Job) -> str:
        """
        Get cleaned text as string (for preview or clipboard).

        Args:
            job: Job to export

        Returns:
            Cleaned text with header/footer
        """
        if not job.cleaned_text:
            return f"# No cleaned text available for: {job.name}"

        output = []
        output.append(f"# Cleaned/Translated: {job.name}")
        output.append(f"# Processed: {job.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"# Source Language: {job.metadata.get('source_lang', 'unknown')}")
        output.append(f"# Target Language: {job.metadata.get('target_lang', 'unknown')}")
        output.append("\n" + "="*80 + "\n")
        output.append(job.cleaned_text)
        output.append("\n" + "="*80)
        output.append(f"# End of {job.name}")

        return '\n'.join(output)
