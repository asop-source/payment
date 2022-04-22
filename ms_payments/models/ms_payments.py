

from odoo import models, fields, api, SUPERUSER_ID, _


class ms_paymements(models.Model):
    _name = 'ms.payments'
    _rec_name = 'name'
    _description = 'Mass Payments'



    name =  fields.Char('Sequence',default='New', copy=False, readonly=True)
    state = fields.Selection([('draft','Draft'),('paid','Paid'),('cancel','Cancelled')], string='State', default='draft')
    vendor_id = fields.Many2one('res.partner','Vendor')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    ms_payments_ids = fields.One2many('ms.payments.line','ms_payments_id','Payments Vendor')
    amount = fields.Float('Amount',compute="get_count", store=True)

    @api.depends('ms_payments_ids.account_move_id')
    def get_count(self):
        dk = []
        for ws in self.ms_payments_ids:
            dk.append(ws.amount)
        self.amount = sum(dk)

    @api.model
    def create(self, vals):
        obj = super(ms_paymements, self).create(vals)
        if obj.name == 'New':
            number = self.env['ir.sequence'].get('seq.ms.payments') or '/'
            obj.sudo().write({'name': number})
        return obj


    def payment_post(self):
        payment = self.env['account.payment']
        outbound = 'outbound'
        ws = payment.with_context(active_ids=self.ids, active_model='ms.payments',active_id=self.id)
        return ws.action_register_ms_payment()
                

    def payment_cancel(self):
        for ln in self.ms_payments_ids:
            self.state = 'cancel'

    def payment_draft(self):
        for ln in self.ms_payments_ids:
            ln.account_move_id.button_draft()
            self.state = 'draft'


class ms_paymements_line(models.Model):
    _name = 'ms.payments.line'
    _rec_name = 'account_move_id'
    _description = 'Mass Payments Line'



    ms_payments_id = fields.Many2one('ms.payments','Mass Payments')
    account_move_id = fields.Many2one('account.move','Bill')
    date = fields.Date('Accounting Date')
    invoice_payment_term_id = fields.Many2one('account.payment.term','Payment Terms')
    amount = fields.Float('Amount')
    state = fields.Selection([('draft','Draft'),('paid','Paid'),('cancel','Cancelled')], string='State', related='ms_payments_id.state')





    @api.onchange('account_move_id')
    def get_amount(self):
        ks = self.account_move_id
        self.amount = ks.amount_untaxed
        self.date = ks.date
        self.invoice_payment_term_id = ks.invoice_payment_term_id.id



class inheritpaymements(models.Model):
    _inherit = 'account.payment'




    def action_register_ms_payment(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''

        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment',
            'view_mode': 'form',
            'view_id': self.env.ref('ms_payments.view_account_mas_payment_invoice_form').id,
            'context': self.env.context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def post_payment(self):
        model = 'ms.payments'
        bk = self.env[model].browse(self.env.context.get('active_id'))
        for line in bk.ms_payments_ids:
            jk = line.account_move_id
            jk.invoice_payment_state = 'paid'
            bk.state = 'paid'
            self.post()
            journal = self.env['account.move.line'].search([
                ('payment_id','=', self.id),
                ('name','=', self.communication)])
            journal.write({'move_id': jk.id})


