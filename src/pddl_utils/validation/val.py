import os
from tempfile import NamedTemporaryFile
from typing import Optional


class VAL:
    """VAL validator"""

    def validate(self, dom_file: str, prob_file: Optional[str], plan_file: Optional[str], remove_files=False) -> tuple[bool, str]:
        tmp_plan_file = NamedTemporaryFile(mode='w', delete=False)
        tmp_plan_file.close()
        if plan_file is not None:
            with open(plan_file, 'r') as f_in, open(tmp_plan_file.name, 'w') as f_out:
                for line in f_in:
                    if not line.strip().startswith(';') and line.strip() != '':
                        f_out.write(line)
        success, output = self._validate(dom_file, prob_file, tmp_plan_file.name)
        os.remove(tmp_plan_file.name)
        if remove_files:
            os.remove(dom_file)
            if prob_file is not None:
                os.remove(prob_file)
            if plan_file is not None:
                os.remove(plan_file)

        if plan_file is not None:
            failed_plan = "Failed plans:" in output
            if not failed_plan:
                assert success
            success = success and not failed_plan

        return success, output

    def _validate(self, dom_file: str, prob_file: Optional[str], plan_file: Optional[str]) -> tuple[bool, str]:
        raise NotImplementedError("Subclasses must implement this method")
