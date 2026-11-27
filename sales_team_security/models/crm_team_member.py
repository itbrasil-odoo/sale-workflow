# Copyright 2026 IT Brasil
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, models


class CrmTeamMember(models.Model):
    _inherit = "crm.team.member"

    # The partner and sale order access domains depend on team membership and
    # are cached: membership changes must drop them.

    def _clear_access_caches(self):
        self.env["ir.access"]._clear_caches()
        self.env.transaction.invalidate_ormcache()

    @api.model_create_multi
    def create(self, vals_list):
        members = super().create(vals_list)
        self._clear_access_caches()
        return members

    def write(self, vals):
        res = super().write(vals)
        self._clear_access_caches()
        return res

    def unlink(self):
        res = super().unlink()
        self._clear_access_caches()
        return res
