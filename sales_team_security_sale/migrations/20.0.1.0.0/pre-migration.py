# Copyright 2026 IT Brasil
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


XMLIDS = (
    "sale_order_team_rule",
    "sale_order_report_team_rule",
    "sale_order_line_team_rule",
)


def migrate(cr, version):
    """The team rules were noupdate ir.rule records up to 19.0 and are ir.access
    lines (security/ir.access.csv) in 20.0, under the same xmlids.

    - An xmlid still pointing to ir.rule would make the CSV load fail with
      "found record of different model": drop it, the CSV recreates the line.
    - An xmlid already converted to ir.access keeps noupdate=True from the old
      XML, so the CSV would never apply: let it be updated.
    """
    if not version:
        return
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'sales_team_security_sale'
           AND name IN %s
           AND model != 'ir.access'
        """,
        (XMLIDS,),
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = FALSE
         WHERE module = 'sales_team_security_sale'
           AND name IN %s
        """,
        (XMLIDS,),
    )
