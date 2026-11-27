# Copyright 2016-2020 Tecnativa - Pedro M. Baeza
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from .common import TestCommon


class TestSalesTeamSecurity(TestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_partner = cls.user.partner_id
        cls.user2_partner = cls.user2.partner_id
        cls.record = cls.partner

    def test_onchange_parent_id(self):
        contact2 = self.env["res.partner"].create(
            {"name": "Test contact", "parent_id": self.partner2.id}
        )
        self.assertEqual(contact2.user_id, self.user)

    def test_change_user_id_partner(self):
        self.partner.write({"user_id": self.user.id})
        self.assertIn(self.user_partner, self.partner.message_partner_ids)
        self.assertNotIn(self.user_partner, self.partner_child_1.message_partner_ids)
        self.assertIn(self.user_partner, self.partner_child_2.message_partner_ids)
        # Change salesman
        self.partner.write({"user_id": self.user2.id})
        self.assertNotIn(self.user_partner, self.partner.message_partner_ids)
        self.assertIn(self.user2_partner, self.partner.message_partner_ids)
        self.assertNotIn(self.user_partner, self.partner_child_2.message_partner_ids)
        self.assertIn(self.user2_partner, self.partner_child_2.message_partner_ids)

    def test_change_user_id_partner_child_1(self):
        self.partner_child_1.write({"user_id": self.user.id})
        self.assertIn(self.user_partner, self.partner.message_partner_ids)
        self.assertIn(self.user_partner, self.partner_child_2.message_partner_ids)
        # Change salesman
        self.partner_child_1.write({"user_id": self.user2.id})
        self.assertNotIn(self.user_partner, self.partner.message_partner_ids)
        self.assertIn(self.user2_partner, self.partner.message_partner_ids)
        self.assertNotIn(self.user_partner, self.partner_child_2.message_partner_ids)
        self.assertIn(self.user2_partner, self.partner_child_2.message_partner_ids)

    def test_partner_permissions(self):
        self._check_whole_permission_set()

    def test_partner_permissions_subscription(self):
        self.check_permission_subscribe = True
        self._check_permission(self.user2, False, True)

    def test_partner_permissions_own_partner(self):
        self.user.partner_id.write({"user_id": self.user2.id})
        domain = [("id", "in", self.user.partner_id.ids)]
        Partner = self.env["res.partner"].with_user(self.user)
        # Make sure the acces is not due to the subscription
        self.partner.message_unsubscribe(partner_ids=self.user.partner_id.ids)
        self.assertEqual(bool(Partner.search(domain)), True)

    def test_team_contacts_visibility(self):
        """Test that users from the same team can see contacts from other salesmen
        in the same team when they have the 'group_sale_team_manager' group
        """
        # Create a user with team manager permissions
        user_manager = self.env["res.users"].create(
            {
                "login": "team_manager",
                "name": "Team Manager",
                "group_ids": [
                    (4, self.env.ref("sales_team.group_sale_salesman").id),
                    (4, self.env.ref("sales_team_security.group_sale_team_manager").id),
                ],
            }
        )
        self.env["crm.team.member"].create(
            {
                "user_id": user_manager.id,
                "crm_team_id": self.team.id,
            }
        )

        # Create another salesman in the same team
        user3 = self.env["res.users"].create(
            {
                "login": "salesman_a",
                "name": "Salesman A",
                "group_ids": [(4, self.env.ref("sales_team.group_sale_salesman").id)],
            }
        )
        self.env["crm.team.member"].create(
            {
                "user_id": user3.id,
                "crm_team_id": self.team.id,
            }
        )

        # Create a contact assigned to user3
        partner_a = self.env["res.partner"].create(
            {"name": "Salesman A Contact", "user_id": user3.id}
        )

        # Verify that user_manager can see the contact created by user3
        partner_a.message_unsubscribe(partner_ids=user_manager.partner_id.ids)
        domain = [("id", "=", partner_a.id)]
        Partner = self.env["res.partner"].with_user(user_manager)
        self.assertTrue(
            bool(Partner.search(domain)),
            "User with team manager group should see contacts from teammates",
        )

    def _team_manager(self):
        manager = self.env["res.users"].create(
            {
                "login": "team_manager_2",
                "name": "Team Manager 2",
                "group_ids": [
                    (4, self.env.ref("sales_team.group_sale_salesman").id),
                    (4, self.env.ref("sales_team_security.group_sale_team_manager").id),
                ],
            }
        )
        self.env["crm.team.member"].create(
            {"user_id": manager.id, "crm_team_id": self.team.id}
        )
        return manager

    def _salesman(self, login, team):
        salesman = self.env["res.users"].create(
            {
                "login": login,
                "name": login,
                "group_ids": [(4, self.env.ref("sales_team.group_sale_salesman").id)],
            }
        )
        member = self.env["crm.team.member"].create(
            {"user_id": salesman.id, "crm_team_id": team.id}
        )
        return salesman, member

    def _sees(self, user, partner):
        partner.message_unsubscribe(partner_ids=user.partner_id.ids)
        return bool(
            self.env["res.partner"].with_user(user).search([("id", "=", partner.id)])
        )

    def test_team_manager_does_not_see_other_teams(self):
        manager = self._team_manager()
        outsider, _member = self._salesman("salesman_outside", self.team2)
        partner = self.env["res.partner"].create(
            {"name": "Other team contact", "user_id": outsider.id}
        )
        self.assertFalse(self._sees(manager, partner))

    def test_team_membership_change_updates_visibility(self):
        manager = self._team_manager()
        salesman, member = self._salesman("salesman_leaving", self.team)
        partner = self.env["res.partner"].create(
            {"name": "Leaving salesman contact", "user_id": salesman.id}
        )
        self.assertTrue(self._sees(manager, partner))
        member.unlink()
        self.assertFalse(self._sees(manager, partner))

    def test_moving_contact_resyncs_followers(self):
        company_x = self.env["res.partner"].create(
            {"name": "Company X", "is_company": True}
        )
        company_y = self.env["res.partner"].create(
            {"name": "Company Y", "is_company": True}
        )
        address = self.env["res.partner"].create(
            {
                "name": "Delivery",
                "type": "delivery",
                "parent_id": company_x.id,
                "user_id": self.user2.id,
            }
        )
        self.assertIn(self.user2.partner_id, company_x.message_partner_ids)
        address.parent_id = company_y
        self.assertIn(self.user2.partner_id, company_y.message_partner_ids)
        self.assertNotIn(self.user2.partner_id, company_x.message_partner_ids)
